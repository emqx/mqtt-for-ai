"""Tests for A2A-over-MQTT responder protocol lifecycle."""

import asyncio
import json
from unittest.mock import AsyncMock

import pytest

from a2a_over_mqtt.protocol import (
    A2ARequest,
    TaskState,
    classify_reply,
    REPLY_ARTIFACT,
    REPLY_TERMINAL,
)
from a2a_over_mqtt.responder import Responder, RoundOutcome
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


class InterruptingResponder(Responder):
    """Test responder that pauses the task for more input."""

    async def on_request(self, request, stream):
        await stream("need input")
        return RoundOutcome(TaskState.INPUT_REQUIRED, "which language?")


class ContinuingResponder(Responder):
    """Test responder that finishes an interrupted task on a continuation."""

    def __init__(self, **kwargs) -> None:
        super().__init__(**kwargs)
        self.continued: list[A2ARequest] = []

    async def on_request(self, request, stream):
        return RoundOutcome(TaskState.INPUT_REQUIRED, "which language?")

    async def on_continue(self, request, stream):
        self.continued.append(request)
        return f"done: {request.text}"


class OutcomeResponder(Responder):
    """Test responder that returns a chosen non-completed outcome."""

    def __init__(self, state: TaskState, **kwargs) -> None:
        super().__init__(**kwargs)
        self._state = state

    async def on_request(self, request, stream):
        return RoundOutcome(self._state, "the reason")


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


class TestRoundOutcome:
    @pytest.mark.asyncio
    async def test_interrupted_outcome_publishes_no_terminal(self):
        responder = _make_responder(InterruptingResponder)
        client = AsyncMock()
        req = A2ARequest(text="hello", request_id="r1", task_id="t1", context_id="c1")

        result = await responder._handle_request(
            client, req, "reply/topic", "corr-1", asyncio.Semaphore(4)
        )

        assert result == "which language?"
        states = [
            json.loads(call.args[1])["result"]["statusUpdate"]["status"]["state"]
            for call in client.publish.call_args_list
        ]
        assert states == [
            "TASK_STATE_SUBMITTED",
            "TASK_STATE_WORKING",
            "TASK_STATE_INPUT_REQUIRED",
        ]

    @pytest.mark.asyncio
    async def test_on_continue_defaults_to_on_request(self):
        responder = _make_responder()
        req = A2ARequest(text="hello", request_id="r1", task_id="t1", context_id="c1")

        assert await responder.on_continue(req, AsyncMock()) == "echo: hello"

    @pytest.mark.asyncio
    async def test_a_continuation_round_calls_on_continue(self):
        responder = _make_responder(ContinuingResponder)
        client = AsyncMock()
        req = A2ARequest(text="简体", request_id="r2", task_id="t1", context_id="c1")

        result = await responder._handle_request(
            client,
            req,
            "reply/topic",
            "corr-2",
            asyncio.Semaphore(4),
            None,
            True,
        )

        assert result == "done: 简体"
        assert [request.text for request in responder.continued] == ["简体"]
        states = [
            json.loads(call.args[1])["result"]["statusUpdate"]["status"]["state"]
            for call in client.publish.call_args_list
            if "statusUpdate" in json.loads(call.args[1])["result"]
        ]
        assert states == ["TASK_STATE_SUBMITTED", "TASK_STATE_COMPLETED"]

    @pytest.mark.asyncio
    async def test_failed_outcome_publishes_failed_with_its_text(self):
        responder = OutcomeResponder(
            TaskState.FAILED,
            agent_id="test-agent",
            mqtt=MqttConfig(),
            topics=TopicSpace(org="test", unit="default"),
            card={"name": "Test"},
        )
        client = AsyncMock()
        req = A2ARequest(text="hello", request_id="r1", task_id="t1", context_id="c1")

        await responder._handle_request(
            client, req, "reply/topic", "corr-1", asyncio.Semaphore(4)
        )

        calls = client.publish.call_args_list
        assert len(calls) == 2
        failed = json.loads(calls[1].args[1])
        status = failed["result"]["statusUpdate"]["status"]
        assert status["state"] == "TASK_STATE_FAILED"
        assert status["message"]["parts"][0]["text"] == "the reason"

    @pytest.mark.asyncio
    async def test_rejected_outcome_publishes_rejected_with_its_text(self):
        responder = OutcomeResponder(
            TaskState.REJECTED,
            agent_id="test-agent",
            mqtt=MqttConfig(),
            topics=TopicSpace(org="test", unit="default"),
            card={"name": "Test"},
        )
        client = AsyncMock()
        req = A2ARequest(text="hello", request_id="r1", task_id="t1", context_id="c1")

        await responder._handle_request(
            client, req, "reply/topic", "corr-1", asyncio.Semaphore(4)
        )

        calls = client.publish.call_args_list
        assert len(calls) == 2
        rejected = json.loads(calls[1].args[1])
        status = rejected["result"]["statusUpdate"]["status"]
        assert status["state"] == "TASK_STATE_REJECTED"
        assert status["message"]["parts"][0]["text"] == "the reason"

    @pytest.mark.asyncio
    async def test_completed_outcome_publishes_artifact_and_terminal(self):
        responder = OutcomeResponder(
            TaskState.COMPLETED,
            agent_id="test-agent",
            mqtt=MqttConfig(),
            topics=TopicSpace(org="test", unit="default"),
            card={"name": "Test"},
        )
        client = AsyncMock()
        req = A2ARequest(text="hello", request_id="r1", task_id="t1", context_id="c1")

        result = await responder._handle_request(
            client, req, "reply/topic", "corr-1", asyncio.Semaphore(4)
        )

        assert result == "the reason"
        assert len(client.publish.call_args_list) == 3
