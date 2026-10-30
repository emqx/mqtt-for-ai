"""A2A-over-MQTT responder: base class for agents that handle requests."""

import abc
import asyncio
import json
import logging
import time
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Protocol

import aiomqtt
from paho.mqtt.packettypes import PacketTypes
from paho.mqtt.properties import Properties

from a2a_over_mqtt.mqtt import (
    MqttConfig,
    get_correlation_data,
    get_response_topic,
    make_properties,
)
from a2a_over_mqtt.protocol import (
    A2A_INVALID_PARAMS,
    A2A_PARSE_ERROR,
    A2A_TASK_NOT_FOUND,
    A2ARequest,
    A2AResponse,
    TaskState,
    ValidationError,
    make_a2a_error,
    make_artifact_event,
    make_status_event,
    validate_a2a_request,
)
from a2a_over_mqtt.topics import TopicSpace

log = logging.getLogger("a2a_over_mqtt.responder")

# TTL for terminal task deduplication (seconds)
_DEDUP_TTL = 300.0

# Soft cap on the task records one responder keeps.  Terminal records are
# evicted first, then the oldest interrupted/working ones.
_MAX_TASKS = 1000

#: The states a task can end in.  An interrupted task is not terminal: the
#: profile lets a later SendMessage on the same Task.id continue it.
_TERMINAL = {
    TaskState.COMPLETED,
    TaskState.FAILED,
    TaskState.CANCELED,
    TaskState.REJECTED,
}
_INTERRUPTED = {TaskState.INPUT_REQUIRED, TaskState.AUTH_REQUIRED}


async def _send_error(
    client: aiomqtt.Client,
    topic: str,
    correlation: str,
    code: int,
    message: str,
) -> None:
    """Publish a JSON-RPC error response to the requester."""
    resp = A2AResponse(id=correlation, error=make_a2a_error(code, message))
    props = make_properties(correlation_data=correlation)
    await client.publish(topic, resp.to_json(), qos=1, properties=props)


@dataclass(frozen=True)
class RoundOutcome:
    """What one request/continuation round ended as.

    ``state`` is ``TaskState.COMPLETED``, ``FAILED``, ``REJECTED``,
    ``INPUT_REQUIRED`` or ``AUTH_REQUIRED``.  The interrupted states keep the
    task open: no artifact and no terminal status are published, and a later
    ``SendMessage`` with the same ``Task.id`` calls :meth:`Responder.on_continue`.

    A plain string (or ``None``) returned from ``on_request`` is the same as
    ``RoundOutcome(TaskState.COMPLETED, text)`` — the existing API is unchanged.
    """

    state: TaskState
    text: str = ""


@dataclass
class _TaskRecord:
    """The responder's view of one task, across rounds."""

    task_id: str
    state: TaskState
    context_id: str = ""
    message_id: str = ""
    result: str = ""
    question: str = ""
    round: int = 1
    seen_ids: set[str] = field(default_factory=set)
    last_text: str = ""
    updated: float = field(default_factory=time.monotonic)

    @property
    def terminal(self) -> bool:
        return self.state in _TERMINAL

    @property
    def interrupted(self) -> bool:
        return self.state in _INTERRUPTED

    def duplicate(self, request: A2ARequest) -> bool:
        """Whether this request is a re-publish of one already accepted.

        The message id is the idempotency key; a peer that sends none falls
        back to the request text.
        """
        if request.message_id:
            return request.message_id in self.seen_ids
        return request.text == self.last_text

    def remember(self, request: A2ARequest) -> None:
        if request.message_id:
            self.seen_ids.add(request.message_id)
        self.last_text = request.text
        self.updated = time.monotonic()


class StreamCallback(Protocol):
    """Callback for sending working status updates during request handling."""

    async def __call__(self, message: str, *, type: str = "text") -> None: ...


class Responder(abc.ABC):
    """Base class for A2A-over-MQTT responders (agents).

    Subclass and implement ``on_request()``. Then call ``run()``.

    Usage::

        class MyAgent(Responder):
            async def on_request(self, request, stream):
                await stream("thinking...")
                return "Here is my result."

        agent = MyAgent(
            agent_id="my-agent",
            mqtt=MqttConfig(host="broker.example.com"),
            topics=TopicSpace(org="myorg"),
            card=build_card(name="My Agent", description="Does things", url="mqtt://broker:1883"),
        )
        await agent.run()
    """

    def __init__(
        self,
        *,
        agent_id: str,
        mqtt: MqttConfig,
        topics: TopicSpace,
        card: dict,
        max_concurrent: int = 4,
    ):
        self._agent_id = agent_id
        self._mqtt = mqtt
        self._topics = topics
        self._card = card
        self._max_concurrent = max_concurrent

    @abc.abstractmethod
    async def on_request(
        self,
        request: A2ARequest,
        stream: StreamCallback,
    ) -> str | None | RoundOutcome:
        """Handle an A2A request. Return artifact text, or None for no artifact.

        Call ``stream("progress message")`` to send working status updates.
        Call ``stream("tool info", type="tool_use")`` for tool-use updates.
        Raise ``asyncio.CancelledError`` to send canceled status.
        Any other exception sends failed status.

        Return a :class:`RoundOutcome` to choose an ending other than
        ``completed``.  ``INPUT_REQUIRED``/``AUTH_REQUIRED`` pause the task;
        a later message with the same ``Task.id`` is handled by
        :meth:`on_continue` instead of this method.
        """

    async def on_continue(
        self,
        request: A2ARequest,
        stream: StreamCallback,
    ) -> str | None | RoundOutcome:
        """Handle a round that continues an interrupted task.

        The default treats it like any other request, which is right for a
        stateless handler.  Override it when the continuation needs the
        question from the earlier round.
        """
        return await self.on_request(request, stream)

    async def run(self) -> None:
        """Connect, publish card, subscribe, handle requests in a loop.

        This is a long-running coroutine. Cancel it or Ctrl-C to stop.
        """
        card_json = json.dumps(self._card)

        # LWT: broker publishes offline card on unexpected disconnect
        lwt_topic = self._topics.discovery(self._agent_id)
        lwt_props = Properties(PacketTypes.WILLMESSAGE)
        lwt_props.UserProperty = [
            ("a2a-status", "offline"),
            ("a2a-status-source", "lwt"),
        ]
        will = aiomqtt.Will(
            topic=lwt_topic,
            payload=card_json,
            qos=1,
            retain=True,
            properties=lwt_props,
        )

        request_topic = self._topics.request(self._agent_id)
        semaphore = asyncio.Semaphore(self._max_concurrent)
        tasks: dict[str, _TaskRecord] = {}
        rounds: dict[str, asyncio.Task] = {}

        async with aiomqtt.Client(
            **self._mqtt.client_kwargs(
                identifier=f"{self._topics.org}/{self._topics.unit}/{self._agent_id}",
                will=will,
            ),
        ) as client:
            try:
                await client.subscribe(request_topic, qos=1)
                # Publish online discovery card with presence User Properties
                online_props = Properties(PacketTypes.PUBLISH)
                online_props.UserProperty = [
                    ("a2a-status", "online"),
                    ("a2a-status-source", "agent"),
                ]
                await client.publish(
                    self._topics.discovery(self._agent_id),
                    card_json,
                    qos=1,
                    retain=True,
                    properties=online_props,
                )
                log.info("Listening on %s", request_topic)

                async for mqtt_msg in client.messages:
                    try:
                        payload = mqtt_msg.payload.decode() if mqtt_msg.payload else ""
                    except (UnicodeDecodeError, AttributeError):
                        payload = ""
                    if not payload:
                        continue

                    # Extract MQTT v5 properties early (needed for error responses)
                    response_topic = get_response_topic(mqtt_msg) or ""
                    correlation = get_correlation_data(mqtt_msg) or ""

                    # Parse JSON; send -32700 error for malformed payloads
                    try:
                        data = json.loads(payload)
                    except json.JSONDecodeError as exc:
                        if response_topic and correlation:
                            await _send_error(
                                client,
                                response_topic,
                                correlation,
                                A2A_PARSE_ERROR,
                                f"Parse error: {exc}",
                            )
                        continue
                    if not isinstance(data, dict):
                        if response_topic and correlation:
                            await _send_error(
                                client,
                                response_topic,
                                correlation,
                                A2A_PARSE_ERROR,
                                "Parse error: payload is not an object",
                            )
                        continue
                    method = data.get("method", "")

                    if method == "CancelTask":
                        await self._on_cancel(
                            client, data, response_topic, correlation, tasks, rounds
                        )
                    elif method == "GetTask":
                        await self._on_get_task(
                            client, data, response_topic, correlation, tasks
                        )
                    elif method == "SendMessage":
                        await self._on_send_message(
                            client,
                            data,
                            response_topic,
                            correlation,
                            semaphore,
                            tasks,
                            rounds,
                        )
                    elif response_topic and correlation:
                        await _send_error(
                            client,
                            response_topic,
                            correlation,
                            -32601,
                            f"Unknown method: {method!r}",
                        )
            finally:
                # Cancel inflight rounds on shutdown
                inflight = list(rounds.values())
                for task in inflight:
                    task.cancel()
                if inflight:
                    await asyncio.gather(*inflight, return_exceptions=True)
                # Publish offline status before disconnect
                try:
                    offline_props = Properties(PacketTypes.PUBLISH)
                    offline_props.UserProperty = [
                        ("a2a-status", "offline"),
                        ("a2a-status-source", "agent"),
                    ]
                    await client.publish(
                        self._topics.discovery(self._agent_id),
                        card_json,
                        qos=1,
                        retain=True,
                        properties=offline_props,
                    )
                except Exception:
                    pass

    # ── Inbound operations ───────────────────────────────────────────────

    async def _on_send_message(
        self,
        client: aiomqtt.Client,
        data: dict,
        response_topic: str,
        correlation: str,
        semaphore: asyncio.Semaphore,
        tasks: dict[str, _TaskRecord],
        rounds: dict[str, asyncio.Task],
    ) -> None:
        result = validate_a2a_request(data, response_topic, correlation)
        if isinstance(result, ValidationError):
            if response_topic:
                await _send_error(
                    client,
                    response_topic,
                    correlation,
                    result.code,
                    result.message,
                )
            return
        req = result
        if not req.task_id:
            return

        self._prune(tasks)
        record = tasks.get(req.task_id)
        if record is None:
            record = _TaskRecord(
                task_id=req.task_id,
                state=TaskState.WORKING,
                context_id=req.context_id or "",
                message_id=req.message_id,
                last_text=req.text,
            )
            record.remember(req)
            tasks[req.task_id] = record
            self._start_round(
                client,
                req,
                response_topic,
                correlation,
                semaphore,
                record,
                rounds,
                continuation=False,
            )
            return

        # Reject context_id mismatch per A2A-over-MQTT spec
        stored_ctx = record.context_id
        incoming_ctx = req.context_id or ""
        if stored_ctx and incoming_ctx and incoming_ctx != stored_ctx:
            log.warning(
                "context_id mismatch for Task.id %s: stored=%s incoming=%s",
                req.task_id,
                stored_ctx,
                incoming_ctx,
            )
            await _send_error(
                client,
                response_topic,
                correlation,
                A2A_INVALID_PARAMS,
                "context_id mismatch: incoming context_id differs "
                "from stored value for this Task.id",
            )
            return

        duplicate = record.duplicate(req)
        if record.state == TaskState.WORKING:
            # A same-Task.id request while a round is running is a retry (the
            # existing dedup behaviour): replay the working state, do not
            # start a second turn.
            await self._replay(client, response_topic, correlation, req, record)
            return
        if record.interrupted:
            if duplicate:
                await self._replay(client, response_topic, correlation, req, record)
                return
            # A new Message on an interrupted task is the continuation.
            record.state = TaskState.WORKING
            record.round += 1
            record.question = ""
            record.remember(req)
            self._start_round(
                client,
                req,
                response_topic,
                correlation,
                semaphore,
                record,
                rounds,
                continuation=True,
            )
            return
        if record.terminal:
            if duplicate:
                await self._replay(client, response_topic, correlation, req, record)
            else:
                await _send_error(
                    client,
                    response_topic,
                    correlation,
                    A2A_INVALID_PARAMS,
                    f"Task {req.task_id} already ended ({record.state.value}) "
                    f"and accepts no further messages",
                )
            return

    def _start_round(
        self,
        client: aiomqtt.Client,
        req: A2ARequest,
        reply_topic: str,
        correlation: str,
        semaphore: asyncio.Semaphore,
        record: _TaskRecord,
        rounds: dict[str, asyncio.Task],
        *,
        continuation: bool,
    ) -> None:
        task = asyncio.create_task(
            self._handle_request(
                client,
                req,
                reply_topic,
                correlation,
                semaphore,
                record,
                continuation,
            )
        )
        rounds[req.task_id] = task

        def _done(t: asyncio.Task, tid: str = req.task_id) -> None:
            if rounds.get(tid) is t:
                rounds.pop(tid, None)

        task.add_done_callback(_done)

    async def _on_cancel(
        self,
        client: aiomqtt.Client,
        data: dict,
        response_topic: str,
        correlation: str,
        tasks: dict[str, _TaskRecord],
        rounds: dict[str, asyncio.Task],
    ) -> None:
        params = data.get("params")
        cancel_id = params.get("id", "") if isinstance(params, dict) else ""
        if not response_topic or not correlation:
            log.warning("CancelTask missing MQTT v5 properties, ignoring")
            return
        request_id = data.get("id", "")
        record = tasks.get(cancel_id)
        if record is None:
            await _send_error(
                client,
                response_topic,
                correlation,
                A2A_INVALID_PARAMS,
                f"Unknown task: {cancel_id}",
            )
            return
        props = make_properties(correlation_data=correlation)
        if record.terminal:
            event = make_status_event(
                request_id=request_id,
                task_id=cancel_id,
                state=record.state.value,
                context_id=record.context_id,
            )
            await client.publish(response_topic, event, qos=1, properties=props)
            return
        if record.interrupted:
            record.state = TaskState.CANCELED
            record.updated = time.monotonic()
            event = make_status_event(
                request_id=request_id,
                task_id=cancel_id,
                state="canceled",
                context_id=record.context_id,
            )
            await client.publish(response_topic, event, qos=1, properties=props)
            log.info("Canceling interrupted task %s", cancel_id)
            return
        task = rounds.get(cancel_id)
        if task is not None:
            task.cancel()
        event = make_status_event(
            request_id=request_id,
            task_id=cancel_id,
            state="canceled",
            context_id=record.context_id,
        )
        await client.publish(response_topic, event, qos=1, properties=props)
        log.info("Canceling task %s", cancel_id)

    async def _on_get_task(
        self,
        client: aiomqtt.Client,
        data: dict,
        response_topic: str,
        correlation: str,
        tasks: dict[str, _TaskRecord],
    ) -> None:
        params = data.get("params")
        task_id = params.get("id", "") if isinstance(params, dict) else ""
        if not response_topic or not correlation:
            log.warning("GetTask missing MQTT v5 properties, ignoring")
            return
        request_id = data.get("id", "")
        record = tasks.get(task_id)
        if record is None:
            await _send_error(
                client,
                response_topic,
                correlation,
                A2A_TASK_NOT_FOUND,
                f"Task not found: {task_id}",
            )
            return
        task = self._task_object(record)
        payload = json.dumps(
            {"jsonrpc": "2.0", "id": request_id, "result": {"task": task}}
        )
        props = make_properties(correlation_data=correlation)
        await client.publish(response_topic, payload, qos=1, properties=props)

    @staticmethod
    def _task_object(record: _TaskRecord) -> dict:
        text = record.question if record.interrupted else record.result
        status: dict = {
            "state": f"TASK_STATE_{record.state.name}",
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
        if text:
            status["message"] = {
                "messageId": uuid.uuid4().hex,
                "role": "ROLE_AGENT",
                "parts": [{"text": text}],
            }
        task: dict = {
            "id": record.task_id,
            "contextId": record.context_id,
            "status": status,
        }
        if record.state == TaskState.COMPLETED and record.result:
            task["artifacts"] = [
                {
                    "artifactId": uuid.uuid4().hex[:12],
                    "parts": [{"text": record.result}],
                }
            ]
        return task

    async def _replay(
        self,
        client: aiomqtt.Client,
        reply_topic: str,
        correlation: str,
        req: A2ARequest,
        record: _TaskRecord,
    ) -> None:
        """Replay the current state of a duplicate request."""
        props = make_properties(correlation_data=correlation)
        if record.state == TaskState.COMPLETED and record.result:
            artifact = make_artifact_event(
                request_id=req.request_id,
                task_id=req.task_id or "",
                artifact_text=record.result,
                context_id=record.context_id,
            )
            await client.publish(reply_topic, artifact, qos=1, properties=props)
        message = record.question if record.interrupted else record.result
        event = make_status_event(
            request_id=req.request_id,
            task_id=req.task_id or "",
            state=record.state.value,
            message=message,
            context_id=record.context_id,
        )
        await client.publish(reply_topic, event, qos=1, properties=props)

    @staticmethod
    def _prune(tasks: dict[str, _TaskRecord]) -> None:
        now = time.monotonic()
        stale = [
            task_id
            for task_id, record in tasks.items()
            if record.terminal and now - record.updated > _DEDUP_TTL
        ]
        for task_id in stale:
            tasks.pop(task_id, None)
        if len(tasks) <= _MAX_TASKS:
            return
        excess = len(tasks) - _MAX_TASKS + 50
        ordered = sorted(
            tasks.values(), key=lambda record: (not record.terminal, record.updated)
        )
        for record in ordered[:excess]:
            tasks.pop(record.task_id, None)

    # ── One round ────────────────────────────────────────────────────────

    async def _handle_request(
        self,
        client: aiomqtt.Client,
        req: A2ARequest,
        reply_topic: str,
        correlation: str,
        semaphore: asyncio.Semaphore,
        record: _TaskRecord | None = None,
        continuation: bool = False,
    ) -> str:
        """Protocol lifecycle for one round.  Returns the result/question text."""
        log.info(
            "Request %s (task %s): %.80s",
            req.request_id,
            req.task_id,
            req.text,
        )
        if record is None:
            record = _TaskRecord(
                task_id=req.task_id or "",
                state=TaskState.WORKING,
                context_id=req.context_id or "",
                message_id=req.message_id,
                last_text=req.text,
            )
            record.remember(req)

        # The stored context is what the task belongs to; a continuation that
        # omits it still gets the original echoed back.
        ctx = record.context_id or req.context_id or ""
        props = make_properties(correlation_data=correlation)
        # Send submitted ack
        ack = make_status_event(
            request_id=req.request_id,
            task_id=req.task_id or "",
            state="submitted",
            context_id=ctx,
        )
        await client.publish(reply_topic, ack, qos=1, properties=props)

        # Stream callback
        async def publish_stream(message: str, *, type: str = "text") -> None:
            event = make_status_event(
                request_id=req.request_id,
                task_id=req.task_id or "",
                state="working",
                message=message,
                context_id=ctx,
                metadata={"type": type},
            )
            await client.publish(reply_topic, event, qos=1, properties=props)

        handler = self.on_continue if continuation else self.on_request
        try:
            async with semaphore:
                result = await handler(req, publish_stream)
        except asyncio.CancelledError:
            record.state = TaskState.CANCELED
            record.result = ""
            record.updated = time.monotonic()
            canceled = make_status_event(
                request_id=req.request_id,
                task_id=req.task_id or "",
                state="canceled",
                message="Task canceled",
                context_id=ctx,
            )
            try:
                await client.publish(reply_topic, canceled, qos=1, properties=props)
            except Exception:
                pass
            log.info("Request %s canceled", req.request_id)
            raise
        except Exception:
            record.state = TaskState.FAILED
            record.result = "Internal error"
            record.updated = time.monotonic()
            log.exception("Request %s failed", req.request_id)
            failed = make_status_event(
                request_id=req.request_id,
                task_id=req.task_id or "",
                state="failed",
                message="Internal error",
                context_id=ctx,
            )
            try:
                await client.publish(reply_topic, failed, qos=1, properties=props)
            except Exception:
                pass
            raise

        outcome = (
            result
            if isinstance(result, RoundOutcome)
            else RoundOutcome(TaskState.COMPLETED, result or "")
        )
        record.updated = time.monotonic()
        if outcome.state in _INTERRUPTED:
            record.state = outcome.state
            record.result = ""
            record.question = outcome.text or ""
            event = make_status_event(
                request_id=req.request_id,
                task_id=req.task_id or "",
                state=outcome.state.value,
                message=record.question,
                context_id=ctx,
            )
            await client.publish(reply_topic, event, qos=1, properties=props)
            log.info(
                "Request %s interrupted (%s)", req.request_id, outcome.state.value
            )
            return record.question
        if outcome.state not in (TaskState.COMPLETED, TaskState.FAILED, TaskState.REJECTED):
            # A handler bug: end the task rather than leave the peer waiting.
            record.state = TaskState.FAILED
            record.result = "Internal error"
            outcome = RoundOutcome(TaskState.FAILED, "Internal error")

        record.state = outcome.state
        record.result = outcome.text or ""
        record.question = ""
        if outcome.state == TaskState.COMPLETED and record.result:
            artifact = make_artifact_event(
                request_id=req.request_id,
                task_id=req.task_id or "",
                artifact_text=record.result,
                context_id=ctx,
            )
            await client.publish(reply_topic, artifact, qos=1, properties=props)
        terminal = make_status_event(
            request_id=req.request_id,
            task_id=req.task_id or "",
            state=outcome.state.value,
            message=record.result if outcome.state != TaskState.COMPLETED else "",
            context_id=ctx,
        )
        await client.publish(reply_topic, terminal, qos=1, properties=props)
        log.info(
            "Request %s %s (%d chars)",
            req.request_id,
            outcome.state.value,
            len(record.result),
        )
        return record.result
