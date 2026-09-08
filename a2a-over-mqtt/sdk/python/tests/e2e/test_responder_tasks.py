"""End-to-end tests for Responder task deduplication and cancellation."""

import asyncio
import json

import pytest
from dirty_equals import IsPartialDict
from zmqtt import MQTTClientV5, PublishProperties, QoS

from a2a_over_mqtt import A2ARequest, TopicSpace
from tests.e2e.responders import ControlledResponder, EchoResponder, ResponderRunner


@pytest.mark.e2e
async def test_responder_deduplicates_active_task(
    controlled_responder: ControlledResponder,
    responder_runner: ResponderRunner,
    mqtt_client: MQTTClientV5,
    topics: TopicSpace,
    agent_id: str,
    a2a_request: A2ARequest,
    correlation_id: str,
    reply_topic: str,
) -> None:
    duplicate_topic = f"{reply_topic}/duplicate"
    async with mqtt_client.subscribe(
        topics.discovery(agent_id),
        qos=QoS.AT_LEAST_ONCE,
    ) as presence:
        responder_task = responder_runner.start(controlled_responder)
        await presence.get_message()

        async with (
            mqtt_client.subscribe(
                reply_topic,
                qos=QoS.AT_LEAST_ONCE,
            ) as first_replies,
            mqtt_client.subscribe(
                duplicate_topic,
                qos=QoS.AT_LEAST_ONCE,
            ) as duplicate_replies,
        ):
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
            submitted = await first_replies.get_message()
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
            working = await first_replies.get_message()
            assert json.loads(working.payload) == IsPartialDict(
                id=a2a_request.request_id,
                result=IsPartialDict(
                    statusUpdate=IsPartialDict(
                        taskId=a2a_request.task_id,
                        contextId=a2a_request.context_id,
                        status=IsPartialDict(
                            state="TASK_STATE_WORKING",
                            message=IsPartialDict(
                                parts=[IsPartialDict(text="waiting for release")]
                            ),
                        ),
                    )
                ),
            )
            await controlled_responder.started.wait()

            duplicate_correlation = f"{correlation_id}-duplicate".encode()
            await mqtt_client.publish(
                topics.request(agent_id),
                a2a_request.to_json(),
                qos=QoS.AT_LEAST_ONCE,
                properties=PublishProperties(
                    response_topic=duplicate_topic,
                    correlation_data=duplicate_correlation,
                ),
            )
            duplicate = await duplicate_replies.get_message()
            assert duplicate.properties is not None
            assert duplicate.properties.correlation_data == duplicate_correlation
            assert json.loads(duplicate.payload) == IsPartialDict(
                id=a2a_request.request_id,
                result=IsPartialDict(
                    statusUpdate=IsPartialDict(
                        taskId=a2a_request.task_id,
                        contextId=a2a_request.context_id,
                        status=IsPartialDict(state="TASK_STATE_WORKING"),
                    )
                ),
            )
            assert controlled_responder.requests == [a2a_request]

            controlled_responder.release.set()
            artifact = await first_replies.get_message()
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
            terminal = await first_replies.get_message()
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

        responder_task.cancel()
        with pytest.raises(asyncio.CancelledError):
            await responder_task


@pytest.mark.e2e
async def test_responder_replays_completed_task(
    echo_responder: EchoResponder,
    responder_runner: ResponderRunner,
    mqtt_client: MQTTClientV5,
    topics: TopicSpace,
    agent_id: str,
    a2a_request: A2ARequest,
    correlation_id: str,
    reply_topic: str,
) -> None:
    duplicate_topic = f"{reply_topic}/duplicate"
    async with mqtt_client.subscribe(
        topics.discovery(agent_id),
        qos=QoS.AT_LEAST_ONCE,
    ) as presence:
        responder_task = responder_runner.start(echo_responder)
        await presence.get_message()

        async with mqtt_client.subscribe(
            reply_topic,
            qos=QoS.AT_LEAST_ONCE,
        ) as first_replies:
            await mqtt_client.publish(
                topics.request(agent_id),
                a2a_request.to_json(),
                qos=QoS.AT_LEAST_ONCE,
                properties=PublishProperties(
                    response_topic=reply_topic,
                    correlation_data=correlation_id.encode(),
                ),
            )
            submitted = await first_replies.get_message()
            assert json.loads(submitted.payload) == IsPartialDict(
                id=a2a_request.request_id,
                result=IsPartialDict(
                    statusUpdate=IsPartialDict(
                        taskId=a2a_request.task_id,
                        status=IsPartialDict(state="TASK_STATE_SUBMITTED"),
                    )
                ),
            )
            working = await first_replies.get_message()
            assert json.loads(working.payload) == IsPartialDict(
                id=a2a_request.request_id,
                result=IsPartialDict(
                    statusUpdate=IsPartialDict(
                        taskId=a2a_request.task_id,
                        status=IsPartialDict(
                            state="TASK_STATE_WORKING",
                            message=IsPartialDict(
                                parts=[IsPartialDict(text="working on it")]
                            ),
                        ),
                    )
                ),
            )
            artifact = await first_replies.get_message()
            assert json.loads(artifact.payload) == IsPartialDict(
                id=a2a_request.request_id,
                result=IsPartialDict(
                    artifactUpdate=IsPartialDict(
                        taskId=a2a_request.task_id,
                        artifact=IsPartialDict(
                            parts=[IsPartialDict(text="echo: hello")]
                        ),
                    )
                ),
            )
            terminal = await first_replies.get_message()
            assert json.loads(terminal.payload) == IsPartialDict(
                id=a2a_request.request_id,
                result=IsPartialDict(
                    statusUpdate=IsPartialDict(
                        taskId=a2a_request.task_id,
                        status=IsPartialDict(state="TASK_STATE_COMPLETED"),
                    )
                ),
            )

        async with mqtt_client.subscribe(
            duplicate_topic,
            qos=QoS.AT_LEAST_ONCE,
        ) as duplicate_replies:
            duplicate_correlation = f"{correlation_id}-duplicate".encode()
            await mqtt_client.publish(
                topics.request(agent_id),
                a2a_request.to_json(),
                qos=QoS.AT_LEAST_ONCE,
                properties=PublishProperties(
                    response_topic=duplicate_topic,
                    correlation_data=duplicate_correlation,
                ),
            )
            artifact = await duplicate_replies.get_message()
            assert artifact.properties is not None
            assert artifact.properties.correlation_data == duplicate_correlation
            assert json.loads(artifact.payload) == IsPartialDict(
                id=a2a_request.request_id,
                result=IsPartialDict(
                    artifactUpdate=IsPartialDict(
                        taskId=a2a_request.task_id,
                        artifact=IsPartialDict(
                            parts=[IsPartialDict(text="echo: hello")]
                        ),
                    )
                ),
            )
            terminal = await duplicate_replies.get_message()
            assert terminal.properties is not None
            assert terminal.properties.correlation_data == duplicate_correlation
            assert json.loads(terminal.payload) == IsPartialDict(
                id=a2a_request.request_id,
                result=IsPartialDict(
                    statusUpdate=IsPartialDict(
                        taskId=a2a_request.task_id,
                        status=IsPartialDict(state="TASK_STATE_COMPLETED"),
                    )
                ),
            )
            assert echo_responder.requests == [a2a_request]

        responder_task.cancel()
        with pytest.raises(asyncio.CancelledError):
            await responder_task


@pytest.mark.e2e
async def test_responder_rejects_duplicate_task_with_different_context(
    controlled_responder: ControlledResponder,
    responder_runner: ResponderRunner,
    mqtt_client: MQTTClientV5,
    topics: TopicSpace,
    agent_id: str,
    a2a_request: A2ARequest,
    mismatched_context_request: A2ARequest,
    correlation_id: str,
    reply_topic: str,
) -> None:
    mismatch_topic = f"{reply_topic}/mismatch"
    async with mqtt_client.subscribe(
        topics.discovery(agent_id),
        qos=QoS.AT_LEAST_ONCE,
    ) as presence:
        responder_task = responder_runner.start(controlled_responder)
        await presence.get_message()

        async with (
            mqtt_client.subscribe(
                reply_topic,
                qos=QoS.AT_LEAST_ONCE,
            ) as first_replies,
            mqtt_client.subscribe(
                mismatch_topic,
                qos=QoS.AT_LEAST_ONCE,
            ) as mismatch_replies,
        ):
            await mqtt_client.publish(
                topics.request(agent_id),
                a2a_request.to_json(),
                qos=QoS.AT_LEAST_ONCE,
                properties=PublishProperties(
                    response_topic=reply_topic,
                    correlation_data=correlation_id.encode(),
                ),
            )
            submitted = await first_replies.get_message()
            assert json.loads(submitted.payload) == IsPartialDict(
                result=IsPartialDict(
                    statusUpdate=IsPartialDict(
                        taskId=a2a_request.task_id,
                        status=IsPartialDict(state="TASK_STATE_SUBMITTED"),
                    )
                )
            )
            working = await first_replies.get_message()
            assert json.loads(working.payload) == IsPartialDict(
                result=IsPartialDict(
                    statusUpdate=IsPartialDict(
                        taskId=a2a_request.task_id,
                        status=IsPartialDict(
                            state="TASK_STATE_WORKING",
                            message=IsPartialDict(
                                parts=[IsPartialDict(text="waiting for release")]
                            ),
                        ),
                    )
                )
            )

            mismatch_correlation = f"{correlation_id}-mismatch".encode()
            await mqtt_client.publish(
                topics.request(agent_id),
                mismatched_context_request.to_json(),
                qos=QoS.AT_LEAST_ONCE,
                properties=PublishProperties(
                    response_topic=mismatch_topic,
                    correlation_data=mismatch_correlation,
                ),
            )
            error_message = await mismatch_replies.get_message()
            assert error_message.properties is not None
            assert error_message.properties.correlation_data == mismatch_correlation
            assert json.loads(error_message.payload) == IsPartialDict(
                error=IsPartialDict(
                    code=-32602,
                    message=(
                        "context_id mismatch: incoming context_id differs from "
                        "stored value for this Task.id"
                    ),
                )
            )
            assert controlled_responder.requests == [a2a_request]

            controlled_responder.release.set()
            artifact = await first_replies.get_message()
            assert json.loads(artifact.payload) == IsPartialDict(
                result=IsPartialDict(
                    artifactUpdate=IsPartialDict(
                        taskId=a2a_request.task_id,
                        artifact=IsPartialDict(
                            parts=[IsPartialDict(text="echo: hello")]
                        ),
                    )
                )
            )
            terminal = await first_replies.get_message()
            assert json.loads(terminal.payload) == IsPartialDict(
                result=IsPartialDict(
                    statusUpdate=IsPartialDict(
                        taskId=a2a_request.task_id,
                        status=IsPartialDict(state="TASK_STATE_COMPLETED"),
                    )
                )
            )

        responder_task.cancel()
        with pytest.raises(asyncio.CancelledError):
            await responder_task


@pytest.mark.e2e
async def test_responder_cancels_active_task(
    controlled_responder: ControlledResponder,
    responder_runner: ResponderRunner,
    mqtt_client: MQTTClientV5,
    topics: TopicSpace,
    agent_id: str,
    a2a_request: A2ARequest,
    correlation_id: str,
    reply_topic: str,
) -> None:
    cancel_topic = f"{reply_topic}/cancel"
    async with mqtt_client.subscribe(
        topics.discovery(agent_id),
        qos=QoS.AT_LEAST_ONCE,
    ) as presence:
        responder_task = responder_runner.start(controlled_responder)
        await presence.get_message()

        async with (
            mqtt_client.subscribe(
                reply_topic,
                qos=QoS.AT_LEAST_ONCE,
            ) as task_replies,
            mqtt_client.subscribe(
                cancel_topic,
                qos=QoS.AT_LEAST_ONCE,
            ) as cancel_replies,
        ):
            await mqtt_client.publish(
                topics.request(agent_id),
                a2a_request.to_json(),
                qos=QoS.AT_LEAST_ONCE,
                properties=PublishProperties(
                    response_topic=reply_topic,
                    correlation_data=correlation_id.encode(),
                ),
            )
            submitted = await task_replies.get_message()
            assert json.loads(submitted.payload) == IsPartialDict(
                result=IsPartialDict(
                    statusUpdate=IsPartialDict(
                        taskId=a2a_request.task_id,
                        status=IsPartialDict(state="TASK_STATE_SUBMITTED"),
                    )
                )
            )
            working = await task_replies.get_message()
            assert json.loads(working.payload) == IsPartialDict(
                result=IsPartialDict(
                    statusUpdate=IsPartialDict(
                        taskId=a2a_request.task_id,
                        status=IsPartialDict(
                            state="TASK_STATE_WORKING",
                            message=IsPartialDict(
                                parts=[IsPartialDict(text="waiting for release")]
                            ),
                        ),
                    )
                )
            )

            cancel_correlation = f"{correlation_id}-cancel".encode()
            await mqtt_client.publish(
                topics.request(agent_id),
                json.dumps(
                    {
                        "jsonrpc": "2.0",
                        "id": f"cancel-{a2a_request.request_id}",
                        "method": "CancelTask",
                        "params": {"id": a2a_request.task_id},
                    }
                ),
                qos=QoS.AT_LEAST_ONCE,
                properties=PublishProperties(
                    response_topic=cancel_topic,
                    correlation_data=cancel_correlation,
                ),
            )
            cancel_reply = await cancel_replies.get_message()
            assert cancel_reply.properties is not None
            assert cancel_reply.properties.correlation_data == cancel_correlation
            assert json.loads(cancel_reply.payload) == IsPartialDict(
                id=f"cancel-{a2a_request.request_id}",
                result=IsPartialDict(
                    statusUpdate=IsPartialDict(
                        taskId=a2a_request.task_id,
                        status=IsPartialDict(state="TASK_STATE_CANCELED"),
                    )
                ),
            )
            canceled = await task_replies.get_message()
            assert json.loads(canceled.payload) == IsPartialDict(
                id=a2a_request.request_id,
                result=IsPartialDict(
                    statusUpdate=IsPartialDict(
                        taskId=a2a_request.task_id,
                        status=IsPartialDict(
                            state="TASK_STATE_CANCELED",
                            message=IsPartialDict(
                                parts=[IsPartialDict(text="Task canceled")]
                            ),
                        ),
                    )
                ),
            )
            assert controlled_responder.requests == [a2a_request]

        responder_task.cancel()
        with pytest.raises(asyncio.CancelledError):
            await responder_task


@pytest.mark.e2e
async def test_responder_handles_cancel_for_completed_and_unknown_tasks(
    echo_responder: EchoResponder,
    responder_runner: ResponderRunner,
    mqtt_client: MQTTClientV5,
    topics: TopicSpace,
    agent_id: str,
    a2a_request: A2ARequest,
    correlation_id: str,
    reply_topic: str,
) -> None:
    completed_cancel_topic = f"{reply_topic}/completed-cancel"
    unknown_cancel_topic = f"{reply_topic}/unknown-cancel"
    async with mqtt_client.subscribe(
        topics.discovery(agent_id),
        qos=QoS.AT_LEAST_ONCE,
    ) as presence:
        responder_task = responder_runner.start(echo_responder)
        await presence.get_message()

        async with mqtt_client.subscribe(
            reply_topic,
            qos=QoS.AT_LEAST_ONCE,
        ) as task_replies:
            await mqtt_client.publish(
                topics.request(agent_id),
                a2a_request.to_json(),
                qos=QoS.AT_LEAST_ONCE,
                properties=PublishProperties(
                    response_topic=reply_topic,
                    correlation_data=correlation_id.encode(),
                ),
            )
            submitted = await task_replies.get_message()
            assert json.loads(submitted.payload) == IsPartialDict(
                result=IsPartialDict(
                    statusUpdate=IsPartialDict(
                        taskId=a2a_request.task_id,
                        status=IsPartialDict(state="TASK_STATE_SUBMITTED"),
                    )
                )
            )
            working = await task_replies.get_message()
            assert json.loads(working.payload) == IsPartialDict(
                result=IsPartialDict(
                    statusUpdate=IsPartialDict(
                        taskId=a2a_request.task_id,
                        status=IsPartialDict(
                            state="TASK_STATE_WORKING",
                            message=IsPartialDict(
                                parts=[IsPartialDict(text="working on it")]
                            ),
                        ),
                    )
                )
            )
            artifact = await task_replies.get_message()
            assert json.loads(artifact.payload) == IsPartialDict(
                result=IsPartialDict(
                    artifactUpdate=IsPartialDict(
                        taskId=a2a_request.task_id,
                        artifact=IsPartialDict(
                            parts=[IsPartialDict(text="echo: hello")]
                        ),
                    )
                )
            )
            terminal = await task_replies.get_message()
            assert json.loads(terminal.payload) == IsPartialDict(
                result=IsPartialDict(
                    statusUpdate=IsPartialDict(
                        taskId=a2a_request.task_id,
                        status=IsPartialDict(state="TASK_STATE_COMPLETED"),
                    )
                )
            )

        async with mqtt_client.subscribe(
            completed_cancel_topic,
            qos=QoS.AT_LEAST_ONCE,
        ) as completed_cancel_replies:
            completed_correlation = f"{correlation_id}-completed".encode()
            await mqtt_client.publish(
                topics.request(agent_id),
                json.dumps(
                    {
                        "jsonrpc": "2.0",
                        "id": f"cancel-{a2a_request.request_id}",
                        "method": "CancelTask",
                        "params": {"id": a2a_request.task_id},
                    }
                ),
                qos=QoS.AT_LEAST_ONCE,
                properties=PublishProperties(
                    response_topic=completed_cancel_topic,
                    correlation_data=completed_correlation,
                ),
            )
            completed_cancel = await completed_cancel_replies.get_message()
            assert completed_cancel.properties is not None
            assert completed_cancel.properties.correlation_data == completed_correlation
            assert json.loads(completed_cancel.payload) == IsPartialDict(
                id=f"cancel-{a2a_request.request_id}",
                result=IsPartialDict(
                    statusUpdate=IsPartialDict(
                        taskId=a2a_request.task_id,
                        status=IsPartialDict(state="TASK_STATE_COMPLETED"),
                    )
                ),
            )

        async with mqtt_client.subscribe(
            unknown_cancel_topic,
            qos=QoS.AT_LEAST_ONCE,
        ) as unknown_cancel_replies:
            unknown_correlation = f"{correlation_id}-unknown".encode()
            await mqtt_client.publish(
                topics.request(agent_id),
                json.dumps(
                    {
                        "jsonrpc": "2.0",
                        "id": f"unknown-{a2a_request.request_id}",
                        "method": "CancelTask",
                        "params": {"id": "unknown-task"},
                    }
                ),
                qos=QoS.AT_LEAST_ONCE,
                properties=PublishProperties(
                    response_topic=unknown_cancel_topic,
                    correlation_data=unknown_correlation,
                ),
            )
            unknown_cancel = await unknown_cancel_replies.get_message()
            assert unknown_cancel.properties is not None
            assert unknown_cancel.properties.correlation_data == unknown_correlation
            assert json.loads(unknown_cancel.payload) == IsPartialDict(
                error=IsPartialDict(
                    code=-32602,
                    message="Unknown task: unknown-task",
                ),
            )

        responder_task.cancel()
        with pytest.raises(asyncio.CancelledError):
            await responder_task
