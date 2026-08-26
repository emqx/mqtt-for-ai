"""End-to-end requester tests for filtering unrelated replies."""

import asyncio
import json

import pytest
from zmqtt import MQTTClientV5, PublishProperties, QoS

from a2a_over_mqtt import A2ARequest, Requester, TopicSpace


@pytest.mark.e2e
async def test_requester_ignores_wrong_correlation(
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
        response_topic = request_message.properties.response_topic
        submitted = json.dumps(
            {
                "jsonrpc": "2.0",
                "id": a2a_request.request_id,
                "result": {
                    "statusUpdate": {
                        "taskId": a2a_request.task_id,
                        "contextId": a2a_request.context_id,
                        "status": {"state": "TASK_STATE_SUBMITTED"},
                    }
                },
            }
        )

        await mqtt_client.publish(
            response_topic,
            submitted,
            qos=QoS.AT_LEAST_ONCE,
            properties=PublishProperties(correlation_data=b"wrong-correlation"),
        )
        with pytest.raises(TimeoutError):
            await asyncio.wait_for(asyncio.shield(stream_task), timeout=0.1)

        response_properties = PublishProperties(
            correlation_data=request_message.properties.correlation_data,
        )
        await mqtt_client.publish(
            response_topic,
            submitted,
            qos=QoS.AT_LEAST_ONCE,
            properties=response_properties,
        )
        assert await stream_task == ("submitted", a2a_request.task_id)
        await mqtt_client.publish(
            response_topic,
            json.dumps(
                {
                    "jsonrpc": "2.0",
                    "id": a2a_request.request_id,
                    "result": {
                        "statusUpdate": {
                            "taskId": a2a_request.task_id,
                            "contextId": a2a_request.context_id,
                            "status": {"state": "TASK_STATE_COMPLETED"},
                        }
                    },
                }
            ),
            qos=QoS.AT_LEAST_ONCE,
            properties=response_properties,
        )
        assert await anext(stream) == ("terminal", "")

        with pytest.raises(StopAsyncIteration):
            await anext(stream)


@pytest.mark.e2e
async def test_requester_ignores_invalid_replies_then_accepts_valid_reply(
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
        response_topic = request_message.properties.response_topic
        response_properties = PublishProperties(
            correlation_data=request_message.properties.correlation_data,
        )

        await mqtt_client.publish(
            response_topic,
            b"",
            qos=QoS.AT_LEAST_ONCE,
            properties=response_properties,
        )
        await mqtt_client.publish(
            response_topic,
            "not-json",
            qos=QoS.AT_LEAST_ONCE,
            properties=response_properties,
        )
        await mqtt_client.publish(
            response_topic,
            json.dumps(
                {
                    "jsonrpc": "2.0",
                    "id": "ignored",
                    "result": {"unknown": {}},
                }
            ),
            qos=QoS.AT_LEAST_ONCE,
            properties=response_properties,
        )
        with pytest.raises(TimeoutError):
            await asyncio.wait_for(asyncio.shield(stream_task), timeout=0.1)

        await mqtt_client.publish(
            response_topic,
            json.dumps(
                {
                    "jsonrpc": "2.0",
                    "id": a2a_request.request_id,
                    "result": {
                        "statusUpdate": {
                            "taskId": a2a_request.task_id,
                            "contextId": a2a_request.context_id,
                            "status": {
                                "state": "TASK_STATE_WORKING",
                                "message": {
                                    "messageId": "valid-update",
                                    "role": "ROLE_AGENT",
                                    "parts": [{"text": "valid reply"}],
                                },
                            },
                        }
                    },
                }
            ),
            qos=QoS.AT_LEAST_ONCE,
            properties=response_properties,
        )
        assert await stream_task == ("text", "valid reply")
        await mqtt_client.publish(
            response_topic,
            json.dumps(
                {
                    "jsonrpc": "2.0",
                    "id": a2a_request.request_id,
                    "result": {
                        "statusUpdate": {
                            "taskId": a2a_request.task_id,
                            "contextId": a2a_request.context_id,
                            "status": {"state": "TASK_STATE_COMPLETED"},
                        }
                    },
                }
            ),
            qos=QoS.AT_LEAST_ONCE,
            properties=response_properties,
        )
        assert await anext(stream) == ("terminal", "")

        with pytest.raises(StopAsyncIteration):
            await anext(stream)
