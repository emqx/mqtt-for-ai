"""A2A-over-MQTT responder: base class for agents that handle requests."""

import abc
import asyncio
import json
import logging
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
    A2ARequest,
    A2AResponse,
    ValidationError,
    make_a2a_error,
    make_artifact_event,
    make_status_event,
    validate_a2a_request,
)
from a2a_over_mqtt.topics import TopicSpace

log = logging.getLogger("a2a_over_mqtt.responder")

# TTL for completed task deduplication (seconds)
_DEDUP_TTL = 300.0


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
    ) -> str | None:
        """Handle an A2A request. Return artifact text, or None for no artifact.

        Call ``stream("progress message")`` to send working status updates.
        Call ``stream("tool info", type="tool_use")`` for tool-use updates.
        Raise ``asyncio.CancelledError`` to send canceled status.
        Any other exception sends failed status.
        """
        ...

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
        task_registry: dict[str, asyncio.Task] = {}  # task_id -> asyncio.Task
        completed_tasks: dict[
            str, tuple[float, str, str]
        ] = {}  # task_id -> (timestamp, state, result)
        task_context: dict[str, str] = {}  # task_id -> context_id

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
                    method = data.get("method", "")

                    if method == "CancelTask":
                        cancel_id = data.get("params", {}).get("id", "")
                        if not response_topic or not correlation:
                            log.warning(
                                "CancelTask missing MQTT v5 properties, ignoring"
                            )
                            continue
                        request_id = data.get("id", "")
                        props = make_properties(correlation_data=correlation)
                        if cancel_id and cancel_id in task_registry:
                            task_registry[cancel_id].cancel()
                            event = make_status_event(
                                request_id=request_id,
                                task_id=cancel_id,
                                state="canceled",
                                context_id=task_context.get(cancel_id, ""),
                            )
                            await client.publish(
                                response_topic, event, qos=1, properties=props
                            )
                            log.info("Canceling task %s", cancel_id)
                        elif cancel_id and cancel_id in completed_tasks:
                            _, state, _ = completed_tasks[cancel_id]
                            event = make_status_event(
                                request_id=request_id,
                                task_id=cancel_id,
                                state=state,
                                context_id=task_context.get(cancel_id, ""),
                            )
                            await client.publish(
                                response_topic, event, qos=1, properties=props
                            )
                        else:
                            await _send_error(
                                client,
                                response_topic,
                                correlation,
                                A2A_INVALID_PARAMS,
                                f"Unknown task: {cancel_id}",
                            )
                        continue

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
                        continue

                    req = result

                    # Task.id deduplication: evict stale entries, return state for known tasks
                    if completed_tasks:
                        now = asyncio.get_running_loop().time()
                        stale = [
                            k
                            for k, v in completed_tasks.items()
                            if now - v[0] > _DEDUP_TTL
                        ]
                        for k in stale:
                            del completed_tasks[k]
                            task_context.pop(k, None)

                    if req.task_id in task_registry:
                        dedup_state, dedup_result = "working", ""
                    elif req.task_id in completed_tasks:
                        _, dedup_state, dedup_result = completed_tasks[req.task_id]
                    else:
                        dedup_state = None
                        dedup_result = None

                    if dedup_state:
                        # Reject context_id mismatch per A2A-over-MQTT spec
                        stored_ctx = task_context.get(req.task_id, "")
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
                            continue

                        log.info(
                            "Duplicate Task.id %s (%s), returning %s state",
                            req.task_id,
                            "in-flight" if dedup_state == "working" else "done",
                            dedup_state,
                        )
                        ctx = req.context_id or ""
                        props = make_properties(correlation_data=correlation)
                        # Replay artifact for completed tasks so retrying requesters
                        # can recover the original output
                        if dedup_result:
                            artifact = make_artifact_event(
                                request_id=req.request_id,
                                task_id=req.task_id,
                                artifact_text=dedup_result,
                                context_id=ctx,
                            )
                            await client.publish(
                                response_topic,
                                artifact,
                                qos=1,
                                properties=props,
                            )
                        event = make_status_event(
                            request_id=req.request_id,
                            task_id=req.task_id,
                            state=dedup_state,
                            context_id=ctx,
                        )
                        await client.publish(
                            response_topic,
                            event,
                            qos=1,
                            properties=props,
                        )
                        continue

                    def _on_done(t: asyncio.Task, tid: str = req.task_id) -> None:
                        task_registry.pop(tid, None)
                        if t.cancelled():
                            state, result = "canceled", ""
                        elif t.exception():
                            log.error("Request handler failed: %s", t.exception())
                            state, result = "failed", ""
                        else:
                            state, result = "completed", t.result() or ""
                        completed_tasks[tid] = (
                            asyncio.get_running_loop().time(),
                            state,
                            result,
                        )

                    task_context[req.task_id] = req.context_id or ""
                    task = asyncio.create_task(
                        self._handle_request(
                            client,
                            req,
                            response_topic,
                            correlation,
                            semaphore,
                        )
                    )
                    task_registry[req.task_id] = task
                    task.add_done_callback(_on_done)
            finally:
                # Cancel inflight tasks on shutdown
                tasks = list(task_registry.values())
                for task in tasks:
                    task.cancel()
                if tasks:
                    await asyncio.gather(*tasks, return_exceptions=True)
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

    async def _handle_request(
        self,
        client: aiomqtt.Client,
        req: A2ARequest,
        reply_topic: str,
        correlation: str,
        semaphore: asyncio.Semaphore,
    ) -> str:
        """Protocol lifecycle: ack -> work -> artifact -> terminal. Returns result text."""
        log.info(
            "Request %s (task %s): %.80s",
            req.request_id,
            req.task_id,
            req.text,
        )

        # Send submitted ack
        ack = make_status_event(
            request_id=req.request_id,
            task_id=req.task_id,
            state="submitted",
            context_id=req.context_id or "",
        )
        props = make_properties(correlation_data=correlation)
        await client.publish(reply_topic, ack, qos=1, properties=props)

        # Stream callback
        async def publish_stream(message: str, *, type: str = "text") -> None:
            event = make_status_event(
                request_id=req.request_id,
                task_id=req.task_id,
                state="working",
                message=message,
                context_id=req.context_id or "",
                metadata={"type": type},
            )
            await client.publish(reply_topic, event, qos=1, properties=props)

        try:
            async with semaphore:
                result = await self.on_request(req, publish_stream)
        except asyncio.CancelledError:
            canceled = make_status_event(
                request_id=req.request_id,
                task_id=req.task_id,
                state="canceled",
                message="Task canceled",
                context_id=req.context_id or "",
            )
            try:
                await client.publish(reply_topic, canceled, qos=1, properties=props)
            except Exception:
                pass
            log.info("Request %s canceled", req.request_id)
            raise
        except Exception:
            log.exception("Request %s failed", req.request_id)
            failed = make_status_event(
                request_id=req.request_id,
                task_id=req.task_id,
                state="failed",
                message="Internal error",
                context_id=req.context_id or "",
            )
            try:
                await client.publish(reply_topic, failed, qos=1, properties=props)
            except Exception:
                pass
            raise

        # Send artifact then terminal status
        result_text = result or ""
        if result_text:
            artifact = make_artifact_event(
                request_id=req.request_id,
                task_id=req.task_id,
                artifact_text=result_text,
                context_id=req.context_id or "",
            )
            await client.publish(reply_topic, artifact, qos=1, properties=props)
        terminal = make_status_event(
            request_id=req.request_id,
            task_id=req.task_id,
            state="completed",
            context_id=req.context_id or "",
        )
        await client.publish(reply_topic, terminal, qos=1, properties=props)
        log.info(
            "Request %s completed (%d chars)",
            req.request_id,
            len(result_text),
        )
        return result_text
