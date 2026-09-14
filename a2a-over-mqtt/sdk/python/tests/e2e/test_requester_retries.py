"""End-to-end requester tests for retries and timeouts."""

import asyncio
import json
from contextlib import aclosing

import pytest
from zmqtt import MQTTClientV5, PublishProperties, QoS

from a2a_over_mqtt import A2ARequest, Requester, TopicSpace


@pytest.mark.e2e
async def test_requester_retries_same_task_with_new_correlation(
    retrying_requester: Requester,
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
        stream = retrying_requester.stream(
            agent_id,
            a2a_request.to_json(),
            correlation_id,
        )

        stream_task = asyncio.create_task(anext(stream))
        first_message = await requests.get_message()
        second_message = await requests.get_message()
        first_request = A2ARequest.from_json(first_message.payload.decode())
        second_request = A2ARequest.from_json(second_message.payload.decode())
        assert first_request == a2a_request
        assert second_request == a2a_request
        assert first_request.task_id == second_request.task_id
        assert first_message.properties is not None
        assert second_message.properties is not None
        assert second_message.properties.response_topic
        assert first_message.properties.correlation_data == correlation_id.encode()
        assert second_message.properties.correlation_data != correlation_id.encode()
        response_properties = PublishProperties(
            correlation_data=second_message.properties.correlation_data,
        )

        await mqtt_client.publish(
            second_message.properties.response_topic,
            json.dumps(
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
            ),
            qos=QoS.AT_LEAST_ONCE,
            properties=response_properties,
        )
        assert await stream_task == ("submitted", a2a_request.task_id)
        await mqtt_client.publish(
            second_message.properties.response_topic,
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
async def test_requester_accepts_late_reply_from_first_attempt(
    retrying_requester: Requester,
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
        stream = retrying_requester.stream(
            agent_id,
            a2a_request.to_json(),
            correlation_id,
        )

        stream_task = asyncio.create_task(anext(stream))
        first_message = await requests.get_message()
        second_message = await requests.get_message()
        assert A2ARequest.from_json(first_message.payload.decode()) == a2a_request
        assert A2ARequest.from_json(second_message.payload.decode()) == a2a_request
        assert first_message.properties is not None
        assert second_message.properties is not None
        assert first_message.properties.response_topic
        assert (
            first_message.properties.correlation_data
            != second_message.properties.correlation_data
        )
        response_properties = PublishProperties(
            correlation_data=first_message.properties.correlation_data,
        )

        await mqtt_client.publish(
            first_message.properties.response_topic,
            json.dumps(
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
            ),
            qos=QoS.AT_LEAST_ONCE,
            properties=response_properties,
        )
        assert await stream_task == ("submitted", a2a_request.task_id)
        await mqtt_client.publish(
            first_message.properties.response_topic,
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
async def test_requester_times_out_when_agent_never_replies(
    timeout_requester: Requester,
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
        stream = timeout_requester.stream(
            agent_id,
            a2a_request.to_json(),
            correlation_id,
        )

        stream_task = asyncio.create_task(anext(stream))
        request_message = await requests.get_message()
        assert A2ARequest.from_json(request_message.payload.decode()) == a2a_request
        assert await stream_task == ("timeout", "")

        with pytest.raises(StopAsyncIteration):
            await anext(stream)


@pytest.mark.e2e
async def test_requester_times_out_when_reply_stream_stalls(
    timeout_requester: Requester,
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
        stream = timeout_requester.stream(
            agent_id,
            a2a_request.to_json(),
            correlation_id,
        )

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
                                "state": "TASK_STATE_WORKING",
                                "message": {
                                    "messageId": "still-working-update",
                                    "role": "ROLE_AGENT",
                                    "parts": [{"text": "still working"}],
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
        assert await stream_task == ("text", "still working")
        loop = asyncio.get_running_loop()
        started_at = loop.time()
        async with asyncio.timeout(1.0):
            reply = await anext(stream)
        assert reply == ("timeout", "")
        assert loop.time() - started_at < 0.5

        with pytest.raises(StopAsyncIteration):
            await anext(stream)


@pytest.mark.e2e
async def test_requester_idle_timeout_does_not_cancel_consumer_processing(
    timeout_requester: Requester,
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
        stream = timeout_requester.stream(
            agent_id,
            a2a_request.to_json(),
            correlation_id,
        )

        async def consume() -> None:
            assert await anext(stream) == ("text", "still working")
            # Processing takes longer than the configured 0.2-second idle timeout.
            await asyncio.sleep(0.3)
            # The expired deadline still applies when reading resumes.
            async with asyncio.timeout(0.1):
                assert await anext(stream) == ("timeout", "")
            with pytest.raises(StopAsyncIteration):
                await anext(stream)

        async with asyncio.timeout(2.0), aclosing(stream), asyncio.TaskGroup() as tasks:
            consumer = tasks.create_task(consume())
            request_message = await requests.get_message()
            assert request_message.properties is not None
            assert request_message.properties.response_topic
            assert (
                request_message.properties.correlation_data == correlation_id.encode()
            )
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
                                    "state": "TASK_STATE_WORKING",
                                    "message": {
                                        "messageId": "working-update",
                                        "role": "ROLE_AGENT",
                                        "parts": [{"text": "still working"}],
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
            await consumer
