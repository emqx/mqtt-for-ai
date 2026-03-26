"""A2A-over-MQTT requester: send requests and stream replies."""

import asyncio
import json
import random
import uuid
from collections.abc import AsyncGenerator

import aiomqtt

from a2a_over_mqtt.mqtt import MqttConfig, get_correlation_data, make_properties
from a2a_over_mqtt.protocol import REPLY_TIMEOUT, TERMINAL_KINDS, classify_reply
from a2a_over_mqtt.topics import TopicSpace

_BACKOFF_BASE = [1.0, 2.0, 4.0]
_JITTER_FACTOR = 0.2


def _backoff_delay(attempt: int) -> float:
    """Exponential backoff with +-20% jitter for retry attempt (0-indexed)."""
    base = _BACKOFF_BASE[min(attempt, len(_BACKOFF_BASE) - 1)]
    jitter = base * _JITTER_FACTOR * (2 * random.random() - 1)
    return base + jitter


class Requester:
    """A2A-over-MQTT requester with retry/timeout support.

    Usage::

        requester = Requester(mqtt_config, topics)
        async for kind, content in requester.stream("my-agent", payload, corr_id):
            print(kind, content)
    """

    def __init__(
        self,
        mqtt: MqttConfig,
        topics: TopicSpace,
        *,
        requester_id: str = "client",
        first_reply_timeout: float = 15.0,
        stream_idle_timeout: float = 30.0,
        max_attempts: int = 3,
    ):
        self._mqtt = mqtt
        self._topics = topics
        self._requester_id = requester_id
        self._first_reply_timeout = first_reply_timeout
        self._stream_idle_timeout = stream_idle_timeout
        self._max_attempts = max_attempts

    async def send(
        self,
        target_agent: str,
        payload: str,
        correlation_id: str,
    ) -> None:
        """Fire-and-forget: publish an A2A request without waiting for replies."""
        session = uuid.uuid4().hex[:12]
        reply_t = self._topics.reply(self._requester_id, session)

        async with aiomqtt.Client(
            **self._mqtt.client_kwargs(
                identifier=f"{self._topics.org}/{self._topics.unit}/{self._requester_id}-{session}",
            ),
        ) as client:
            props = make_properties(
                response_topic=reply_t,
                correlation_data=correlation_id,
            )
            await client.publish(
                self._topics.request(target_agent),
                payload,
                qos=1,
                properties=props,
            )

    async def stream(
        self,
        target_agent: str,
        payload: str,
        correlation_id: str,
    ) -> AsyncGenerator[tuple[str, str], None]:
        """Publish a request and yield (kind, content) reply tuples.

        Implements the A2A requester retry/timeout profile: retries with new
        Correlation Data on first-reply timeout, validates Correlation Data
        on incoming messages. Yields ("timeout", "") if all attempts are
        exhausted or the stream stalls after receiving at least one reply.
        """
        session = uuid.uuid4().hex[:12]
        reply_t = self._topics.reply(self._requester_id, session)

        async with aiomqtt.Client(
            **self._mqtt.client_kwargs(
                identifier=f"{self._topics.org}/{self._topics.unit}/{self._requester_id}-{session}",
            ),
        ) as client:
            await client.subscribe(reply_t, qos=1)

            got_first_reply = False
            current_correlation = correlation_id
            # Accept replies matching any correlation from prior attempts,
            # since the responder echoes the correlation from the first
            # request it received (dedup drops retries by Task.id).
            valid_correlations: set[str] = {correlation_id}

            for attempt in range(self._max_attempts):
                if attempt > 0:
                    delay = _backoff_delay(attempt - 1)
                    await asyncio.sleep(delay)
                    # New Correlation Data per retry, same Task.id in payload
                    current_correlation = uuid.uuid4().hex[:16]
                    valid_correlations.add(current_correlation)

                props = make_properties(
                    response_topic=reply_t,
                    correlation_data=current_correlation,
                )
                await client.publish(
                    self._topics.request(target_agent),
                    payload,
                    qos=1,
                    properties=props,
                )

                try:
                    loop = asyncio.get_running_loop()
                    cm = asyncio.timeout_at(loop.time() + self._first_reply_timeout)
                    async with cm:
                        async for mqtt_msg in client.messages:
                            msg_corr = get_correlation_data(mqtt_msg)
                            if msg_corr not in valid_correlations:
                                continue

                            raw = mqtt_msg.payload.decode() if mqtt_msg.payload else ""
                            if not raw:
                                continue

                            try:
                                data = json.loads(raw)
                            except Exception:
                                continue

                            kind, content = classify_reply(data)
                            if not kind:
                                continue

                            got_first_reply = True
                            cm.reschedule(loop.time() + self._stream_idle_timeout)

                            yield kind, content
                            if kind in TERMINAL_KINDS:
                                return
                except TimeoutError:
                    if got_first_reply:
                        yield REPLY_TIMEOUT, ""
                        return
                    # No reply at all: retry (next attempt)
                    continue

            # All attempts exhausted
            yield REPLY_TIMEOUT, ""
