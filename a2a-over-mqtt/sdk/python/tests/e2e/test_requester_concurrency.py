"""End-to-end requester tests for concurrent streams."""

import asyncio
import json

import pytest
from zmqtt import MQTTClientV5, PublishProperties, QoS

from a2a_over_mqtt import A2ARequest, Requester, TopicSpace


@pytest.mark.e2e
async def test_concurrent_request_streams_do_not_cross_deliver_replies(
    requester: Requester,
    mqtt_client: MQTTClientV5,
    topics: TopicSpace,
    agent_id: str,
    parallel_requests: tuple[A2ARequest, A2ARequest],
    parallel_correlation_ids: tuple[str, str],
) -> None:
    first_request, second_request = parallel_requests
    first_correlation, second_correlation = parallel_correlation_ids

    async with mqtt_client.subscribe(
        topics.request(agent_id),
        qos=QoS.AT_LEAST_ONCE,
    ) as requests:
        first_stream = requester.stream(
            agent_id,
            first_request.to_json(),
            first_correlation,
        )
        first_reply_task = asyncio.create_task(anext(first_stream))
        first_message = await requests.get_message()
        received_first_request = A2ARequest.from_json(first_message.payload.decode())
        assert received_first_request == first_request
        assert first_message.properties is not None
        assert first_message.properties.response_topic
        first_response_properties = PublishProperties(
            correlation_data=first_message.properties.correlation_data,
        )
        await mqtt_client.publish(
            first_message.properties.response_topic,
            json.dumps(
                {
                    "jsonrpc": "2.0",
                    "id": first_request.request_id,
                    "result": {
                        "statusUpdate": {
                            "taskId": first_request.task_id,
                            "contextId": first_request.context_id,
                            "status": {"state": "TASK_STATE_SUBMITTED"},
                        }
                    },
                }
            ),
            qos=QoS.AT_LEAST_ONCE,
            properties=first_response_properties,
        )
        assert await first_reply_task == (
            "submitted",
            first_request.task_id,
        )

        second_stream = requester.stream(
            agent_id,
            second_request.to_json(),
            second_correlation,
        )
        second_reply_task = asyncio.create_task(anext(second_stream))
        second_message = await requests.get_message()
        received_second_request = A2ARequest.from_json(second_message.payload.decode())
        assert received_second_request == second_request
        assert second_message.properties is not None
        assert second_message.properties.response_topic
        second_response_properties = PublishProperties(
            correlation_data=second_message.properties.correlation_data,
        )
        await mqtt_client.publish(
            second_message.properties.response_topic,
            json.dumps(
                {
                    "jsonrpc": "2.0",
                    "id": second_request.request_id,
                    "result": {
                        "statusUpdate": {
                            "taskId": second_request.task_id,
                            "contextId": second_request.context_id,
                            "status": {"state": "TASK_STATE_SUBMITTED"},
                        }
                    },
                }
            ),
            qos=QoS.AT_LEAST_ONCE,
            properties=second_response_properties,
        )
        assert await second_reply_task == (
            "submitted",
            second_request.task_id,
        )

        await mqtt_client.publish(
            second_message.properties.response_topic,
            json.dumps(
                {
                    "jsonrpc": "2.0",
                    "id": second_request.request_id,
                    "result": {
                        "statusUpdate": {
                            "taskId": second_request.task_id,
                            "contextId": second_request.context_id,
                            "status": {
                                "state": "TASK_STATE_WORKING",
                                "message": {
                                    "messageId": "second-update",
                                    "role": "ROLE_AGENT",
                                    "parts": [{"text": "reply to second"}],
                                },
                            },
                        }
                    },
                }
            ),
            qos=QoS.AT_LEAST_ONCE,
            properties=second_response_properties,
        )
        assert await anext(second_stream) == (
            "text",
            "reply to second",
        )
        await mqtt_client.publish(
            first_message.properties.response_topic,
            json.dumps(
                {
                    "jsonrpc": "2.0",
                    "id": first_request.request_id,
                    "result": {
                        "statusUpdate": {
                            "taskId": first_request.task_id,
                            "contextId": first_request.context_id,
                            "status": {
                                "state": "TASK_STATE_WORKING",
                                "message": {
                                    "messageId": "first-update",
                                    "role": "ROLE_AGENT",
                                    "parts": [{"text": "reply to first"}],
                                },
                            },
                        }
                    },
                }
            ),
            qos=QoS.AT_LEAST_ONCE,
            properties=first_response_properties,
        )
        assert await anext(first_stream) == (
            "text",
            "reply to first",
        )

        await mqtt_client.publish(
            second_message.properties.response_topic,
            json.dumps(
                {
                    "jsonrpc": "2.0",
                    "id": second_request.request_id,
                    "result": {
                        "statusUpdate": {
                            "taskId": second_request.task_id,
                            "contextId": second_request.context_id,
                            "status": {"state": "TASK_STATE_COMPLETED"},
                        }
                    },
                }
            ),
            qos=QoS.AT_LEAST_ONCE,
            properties=second_response_properties,
        )
        assert await anext(second_stream) == (
            "terminal",
            "",
        )
        await mqtt_client.publish(
            first_message.properties.response_topic,
            json.dumps(
                {
                    "jsonrpc": "2.0",
                    "id": first_request.request_id,
                    "result": {
                        "statusUpdate": {
                            "taskId": first_request.task_id,
                            "contextId": first_request.context_id,
                            "status": {"state": "TASK_STATE_COMPLETED"},
                        }
                    },
                }
            ),
            qos=QoS.AT_LEAST_ONCE,
            properties=first_response_properties,
        )
        assert await anext(first_stream) == (
            "terminal",
            "",
        )

        with pytest.raises(StopAsyncIteration):
            await anext(first_stream)
        with pytest.raises(StopAsyncIteration):
            await anext(second_stream)
