"""End-to-end requester tests for final agent responses."""

import asyncio
import json

import pytest
from zmqtt import MQTTClientV5, PublishProperties, QoS

from a2a_over_mqtt import A2ARequest, Requester, TopicSpace


@pytest.mark.e2e
@pytest.mark.parametrize(
    ("wire_state", "message", "expected_reply"),
    [
        ("TASK_STATE_COMPLETED", "", ("terminal", "")),
        ("TASK_STATE_FAILED", "agent crashed", ("failed", "agent crashed")),
        ("TASK_STATE_CANCELED", "user canceled", ("failed", "user canceled")),
        (
            "TASK_STATE_REJECTED",
            "request rejected",
            ("failed", "request rejected"),
        ),
        (
            "TASK_STATE_INPUT_REQUIRED",
            "provide a location",
            ("input_required", "provide a location"),
        ),
        (
            "TASK_STATE_AUTH_REQUIRED",
            "sign in",
            ("input_required", "sign in"),
        ),
    ],
    ids=[
        "completed",
        "failed",
        "canceled",
        "rejected",
        "input-required",
        "auth-required",
    ],
)
async def test_requester_receives_terminal_status(
    requester: Requester,
    mqtt_client: MQTTClientV5,
    topics: TopicSpace,
    agent_id: str,
    a2a_request: A2ARequest,
    correlation_id: str,
    wire_state: str,
    message: str,
    expected_reply: tuple[str, str],
) -> None:
    async with mqtt_client.subscribe(
        topics.request(agent_id),
        qos=QoS.AT_LEAST_ONCE,
    ) as requests:
        stream = requester.stream(agent_id, a2a_request.to_json(), correlation_id)

        stream_task = asyncio.create_task(anext(stream))
        request_message = await requests.get_message()
        assert A2ARequest.from_json(request_message.payload.decode()) == a2a_request
        assert request_message.properties is not None
        assert request_message.properties.response_topic
        assert request_message.properties.correlation_data == correlation_id.encode()

        await mqtt_client.publish(
            request_message.properties.response_topic,
            json.dumps(
                {
                    "jsonrpc": "2.0",
                    "id": a2a_request.request_id,
                    "result": {
                        "statusUpdate": {
                            "taskId": a2a_request.task_id,
                            "contextId": a2a_request.context_id,
                            "status": {
                                "state": wire_state,
                                "message": {
                                    "messageId": "terminal-update",
                                    "role": "ROLE_AGENT",
                                    "parts": [{"text": message}],
                                },
                            },
                        }
                    },
                }
            ),
            qos=QoS.AT_LEAST_ONCE,
            properties=PublishProperties(
                correlation_data=request_message.properties.correlation_data,
            ),
        )
        assert await stream_task == expected_reply

        with pytest.raises(StopAsyncIteration):
            await anext(stream)


@pytest.mark.e2e
async def test_requester_receives_json_rpc_error(
    requester: Requester,
    mqtt_client: MQTTClientV5,
    topics: TopicSpace,
    agent_id: str,
    a2a_request: A2ARequest,
    correlation_id: str,
) -> None:
    async with mqtt_client.subscribe(
        topics.request(agent_id),
        qos=QoS.AT_LEAST_ONCE,
    ) as requests:
        stream = requester.stream(agent_id, a2a_request.to_json(), correlation_id)

        stream_task = asyncio.create_task(anext(stream))
        request_message = await requests.get_message()
        assert A2ARequest.from_json(request_message.payload.decode()) == a2a_request
        assert request_message.properties is not None
        assert request_message.properties.response_topic
        assert request_message.properties.correlation_data == correlation_id.encode()

        await mqtt_client.publish(
            request_message.properties.response_topic,
            json.dumps(
                {
                    "jsonrpc": "2.0",
                    "id": a2a_request.request_id,
                    "error": {
                        "code": -32004,
                        "message": "agent offline",
                        "data": {"a2a_error": "responder_unavailable"},
                    },
                }
            ),
            qos=QoS.AT_LEAST_ONCE,
            properties=PublishProperties(
                correlation_data=request_message.properties.correlation_data,
            ),
        )
        assert await stream_task == ("error", "agent offline")

        with pytest.raises(StopAsyncIteration):
            await anext(stream)
