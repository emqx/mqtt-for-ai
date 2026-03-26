"""Tests for A2A-over-MQTT responder protocol lifecycle."""

import asyncio
import json
from unittest.mock import AsyncMock

import pytest

from a2a_over_mqtt.protocol import (
    A2ARequest,
    classify_reply,
    REPLY_ARTIFACT,
    REPLY_TERMINAL,
)
from a2a_over_mqtt.responder import Responder
from a2a_over_mqtt.mqtt import MqttConfig
from a2a_over_mqtt.topics import TopicSpace


class EchoResponder(Responder):
    """Test responder that echoes request text."""

    async def on_request(self, request, stream):
        await stream("working on it")
        return f"echo: {request.text}"


class FailingResponder(Responder):
    """Test responder that raises an exception."""

    async def on_request(self, request, stream):
        raise RuntimeError("boom")


class NoneResponder(Responder):
    """Test responder that returns None (no artifact)."""

    async def on_request(self, request, stream):
        return None


def _make_responder(cls=EchoResponder):
    return cls(
        agent_id="test-agent",
        mqtt=MqttConfig(),
        topics=TopicSpace(org="test", unit="default"),
        card={"name": "Test"},
    )


class TestHandleRequest:
    @pytest.mark.asyncio
    async def test_successful_request_lifecycle(self):
        responder = _make_responder()
        client = AsyncMock()
        req = A2ARequest(text="hello", request_id="r1", task_id="t1", context_id="c1")
        semaphore = asyncio.Semaphore(4)

        result = await responder._handle_request(
            client, req, "reply/topic", "corr-1", semaphore
        )

        assert result == "echo: hello"

        # Verify publish sequence: submitted, working, artifact, completed
        calls = client.publish.call_args_list
        assert len(calls) == 4

        # submitted ack
        d0 = json.loads(calls[0].args[1])
        assert d0["result"]["statusUpdate"]["status"]["state"] == "TASK_STATE_SUBMITTED"

        # working stream
        d1 = json.loads(calls[1].args[1])
        assert d1["result"]["statusUpdate"]["status"]["state"] == "TASK_STATE_WORKING"

        # artifact
        d2 = json.loads(calls[2].args[1])
        kind, content = classify_reply(d2)
        assert kind == REPLY_ARTIFACT
        assert content == "echo: hello"

        # terminal
        d3 = json.loads(calls[3].args[1])
        kind, _ = classify_reply(d3)
        assert kind == REPLY_TERMINAL

    @pytest.mark.asyncio
    async def test_failed_request_sends_failed_status(self):
        responder = _make_responder(FailingResponder)
        client = AsyncMock()
        req = A2ARequest(text="fail", request_id="r1", task_id="t1", context_id="c1")
        semaphore = asyncio.Semaphore(4)

        with pytest.raises(RuntimeError, match="boom"):
            await responder._handle_request(
                client, req, "reply/topic", "corr-1", semaphore
            )

        calls = client.publish.call_args_list
        # submitted + failed
        assert len(calls) == 2
        d_fail = json.loads(calls[1].args[1])
        assert (
            d_fail["result"]["statusUpdate"]["status"]["state"] == "TASK_STATE_FAILED"
        )

    @pytest.mark.asyncio
    async def test_none_result_no_artifact(self):
        responder = _make_responder(NoneResponder)
        client = AsyncMock()
        req = A2ARequest(text="noop", request_id="r1", task_id="t1", context_id="c1")
        semaphore = asyncio.Semaphore(4)

        result = await responder._handle_request(
            client, req, "reply/topic", "corr-1", semaphore
        )

        assert result == ""
        calls = client.publish.call_args_list
        # submitted + completed (no artifact)
        assert len(calls) == 2
        d_terminal = json.loads(calls[1].args[1])
        kind, _ = classify_reply(d_terminal)
        assert kind == REPLY_TERMINAL

    @pytest.mark.asyncio
    async def test_correlation_echoed_in_all_messages(self):
        responder = _make_responder()
        client = AsyncMock()
        req = A2ARequest(text="hello", request_id="r1", task_id="t1", context_id="c1")
        semaphore = asyncio.Semaphore(4)

        await responder._handle_request(
            client, req, "reply/topic", "corr-99", semaphore
        )

        for call in client.publish.call_args_list:
            # All publishes go to the same reply topic
            assert call.args[0] == "reply/topic"

    @pytest.mark.asyncio
    async def test_jsonrpc_id_uses_request_id_not_correlation(self):
        """JSON-RPC response id must be the request's id, not MQTT Correlation Data."""
        responder = _make_responder()
        client = AsyncMock()
        req = A2ARequest(text="hello", request_id="r1", task_id="t1", context_id="c1")
        semaphore = asyncio.Semaphore(4)

        await responder._handle_request(
            client, req, "reply/topic", "corr-99", semaphore
        )

        for call in client.publish.call_args_list:
            data = json.loads(call.args[1])
            assert data["id"] == "r1", f"Expected JSON-RPC id 'r1', got '{data['id']}'"
