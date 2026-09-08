"""End-to-end tests for the production Paho-based Responder."""

import asyncio
import json

import pytest
from dirty_equals import IsPartialDict
from zmqtt import MQTTClientV5, PublishProperties, QoS

from a2a_over_mqtt import A2ARequest, TopicSpace
from tests.e2e.responders import EchoResponder, ResponderRunner


@pytest.mark.e2e
async def test_responder_serves_success_stream_to_zmqtt_requester(
    echo_responder: EchoResponder,
    responder_runner: ResponderRunner,
    mqtt_client: MQTTClientV5,
    topics: TopicSpace,
    agent_id: str,
    agent_card: dict,
    a2a_request: A2ARequest,
    correlation_id: str,
    reply_topic: str,
) -> None:
    async with mqtt_client.subscribe(
        topics.discovery(agent_id),
        qos=QoS.AT_LEAST_ONCE,
        retain_as_published=True,
    ) as presence:
        responder_task = responder_runner.start(echo_responder)
        online_message = await presence.get_message()
        assert json.loads(online_message.payload) == agent_card
        assert online_message.properties is not None
        assert dict(online_message.properties.user_properties) == {
            "a2a-status": "online",
            "a2a-status-source": "agent",
        }

        async with mqtt_client.subscribe(
            reply_topic,
            qos=QoS.AT_LEAST_ONCE,
        ) as replies:
            correlation_data = correlation_id.encode()
            await mqtt_client.publish(
                topics.request(agent_id),
                a2a_request.to_json(),
                qos=QoS.AT_LEAST_ONCE,
                properties=PublishProperties(
                    response_topic=reply_topic,
                    correlation_data=correlation_data,
                ),
            )

            submitted = await replies.get_message()
            assert submitted.properties is not None
            assert submitted.properties.correlation_data == correlation_data
            assert json.loads(submitted.payload) == IsPartialDict(
                id=a2a_request.request_id,
                result=IsPartialDict(
                    statusUpdate=IsPartialDict(
                        taskId=a2a_request.task_id,
                        contextId=a2a_request.context_id,
                        status=IsPartialDict(state="TASK_STATE_SUBMITTED"),
                    )
                ),
            )
            working = await replies.get_message()
            assert working.properties is not None
            assert working.properties.correlation_data == correlation_data
            assert json.loads(working.payload) == IsPartialDict(
                id=a2a_request.request_id,
                result=IsPartialDict(
                    statusUpdate=IsPartialDict(
                        taskId=a2a_request.task_id,
                        contextId=a2a_request.context_id,
                        status=IsPartialDict(
                            state="TASK_STATE_WORKING",
                            message=IsPartialDict(
                                role="ROLE_AGENT",
                                parts=[IsPartialDict(text="working on it")],
                            ),
                        ),
                    )
                ),
            )
            artifact = await replies.get_message()
            assert artifact.properties is not None
            assert artifact.properties.correlation_data == correlation_data
            assert json.loads(artifact.payload) == IsPartialDict(
                id=a2a_request.request_id,
                result=IsPartialDict(
                    artifactUpdate=IsPartialDict(
                        taskId=a2a_request.task_id,
                        contextId=a2a_request.context_id,
                        artifact=IsPartialDict(
                            parts=[IsPartialDict(text="echo: hello")]
                        ),
                    )
                ),
            )
            terminal = await replies.get_message()
            assert terminal.properties is not None
            assert terminal.properties.correlation_data == correlation_data
            assert json.loads(terminal.payload) == IsPartialDict(
                id=a2a_request.request_id,
                result=IsPartialDict(
                    statusUpdate=IsPartialDict(
                        taskId=a2a_request.task_id,
                        contextId=a2a_request.context_id,
                        status=IsPartialDict(state="TASK_STATE_COMPLETED"),
                    )
                ),
            )
            assert echo_responder.requests == [a2a_request]

        responder_task.cancel()
        with pytest.raises(asyncio.CancelledError):
            await responder_task
