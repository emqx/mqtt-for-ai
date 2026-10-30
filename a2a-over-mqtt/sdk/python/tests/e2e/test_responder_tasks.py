"""End-to-end tests for Responder task deduplication and cancellation."""

import asyncio
import json

import pytest
from dirty_equals import IsPartialDict
from zmqtt import MQTTClientV5, PublishProperties, QoS

from a2a_over_mqtt import A2ARequest, TopicSpace
from tests.e2e.responders import (
    ControlledResponder,
    EchoResponder,
    InterruptingResponder,
    ResponderRunner,
)


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


@pytest.mark.e2e
async def test_responder_continues_interrupted_task(
    interrupting_responder: InterruptingResponder,
    responder_runner: ResponderRunner,
    mqtt_client: MQTTClientV5,
    topics: TopicSpace,
    agent_id: str,
    a2a_request: A2ARequest,
    continuation_request: A2ARequest,
    correlation_id: str,
    reply_topic: str,
) -> None:
    continuation_topic = f"{reply_topic}/continuation"
    get_topic = f"{reply_topic}/get"
    new_topic = f"{reply_topic}/new"

    async with mqtt_client.subscribe(
        topics.discovery(agent_id),
        qos=QoS.AT_LEAST_ONCE,
    ) as presence:
        responder_task = responder_runner.start(interrupting_responder)
        await presence.get_message()

        async with (
            mqtt_client.subscribe(
                reply_topic,
                qos=QoS.AT_LEAST_ONCE,
            ) as replies,
            mqtt_client.subscribe(
                continuation_topic,
                qos=QoS.AT_LEAST_ONCE,
            ) as continuation_replies,
            mqtt_client.subscribe(
                get_topic,
                qos=QoS.AT_LEAST_ONCE,
            ) as get_replies,
            mqtt_client.subscribe(
                new_topic,
                qos=QoS.AT_LEAST_ONCE,
            ) as new_replies,
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
            submitted = await replies.get_message()
            assert json.loads(submitted.payload) == IsPartialDict(
                result=IsPartialDict(
                    statusUpdate=IsPartialDict(
                        taskId=a2a_request.task_id,
                        status=IsPartialDict(state="TASK_STATE_SUBMITTED"),
                    )
                )
            )
            working = await replies.get_message()
            assert json.loads(working.payload) == IsPartialDict(
                result=IsPartialDict(
                    statusUpdate=IsPartialDict(
                        taskId=a2a_request.task_id,
                        status=IsPartialDict(
                            state="TASK_STATE_WORKING",
                            message=IsPartialDict(
                                parts=[IsPartialDict(text="need more input")]
                            ),
                        ),
                    )
                )
            )
            interrupted = await replies.get_message()
            assert json.loads(interrupted.payload) == IsPartialDict(
                id=a2a_request.request_id,
                result=IsPartialDict(
                    statusUpdate=IsPartialDict(
                        taskId=a2a_request.task_id,
                        contextId=a2a_request.context_id,
                        status=IsPartialDict(
                            state="TASK_STATE_INPUT_REQUIRED",
                            message=IsPartialDict(
                                parts=[IsPartialDict(text="which language?")]
                            ),
                        ),
                    )
                ),
            )

            # GetTask reports the paused task, question included.
            get_correlation = f"{correlation_id}-get".encode()
            await mqtt_client.publish(
                topics.request(agent_id),
                json.dumps(
                    {
                        "jsonrpc": "2.0",
                        "id": f"get-{a2a_request.request_id}",
                        "method": "GetTask",
                        "params": {"id": a2a_request.task_id},
                    }
                ),
                qos=QoS.AT_LEAST_ONCE,
                properties=PublishProperties(
                    response_topic=get_topic,
                    correlation_data=get_correlation,
                ),
            )
            task_reply = await get_replies.get_message()
            assert task_reply.properties is not None
            assert task_reply.properties.correlation_data == get_correlation
            task = json.loads(task_reply.payload)["result"]["task"]
            assert task["id"] == a2a_request.task_id
            assert task["contextId"] == a2a_request.context_id
            assert task["status"]["state"] == "TASK_STATE_INPUT_REQUIRED"
            assert task["status"]["message"]["parts"][0]["text"] == "which language?"

            # The continuation: same Task.id and context, a new Message.
            continuation_correlation = f"{correlation_id}-continuation".encode()
            await mqtt_client.publish(
                topics.request(agent_id),
                continuation_request.to_json(),
                qos=QoS.AT_LEAST_ONCE,
                properties=PublishProperties(
                    response_topic=continuation_topic,
                    correlation_data=continuation_correlation,
                ),
            )
            c_submitted = await continuation_replies.get_message()
            assert json.loads(c_submitted.payload) == IsPartialDict(
                result=IsPartialDict(
                    statusUpdate=IsPartialDict(
                        taskId=a2a_request.task_id,
                        status=IsPartialDict(state="TASK_STATE_SUBMITTED"),
                    )
                )
            )
            c_working = await continuation_replies.get_message()
            assert json.loads(c_working.payload) == IsPartialDict(
                result=IsPartialDict(
                    statusUpdate=IsPartialDict(
                        taskId=a2a_request.task_id,
                        status=IsPartialDict(
                            state="TASK_STATE_WORKING",
                            message=IsPartialDict(
                                parts=[IsPartialDict(text="continuing")]
                            ),
                        ),
                    )
                )
            )
            c_artifact = await continuation_replies.get_message()
            assert json.loads(c_artifact.payload) == IsPartialDict(
                result=IsPartialDict(
                    artifactUpdate=IsPartialDict(
                        taskId=a2a_request.task_id,
                        artifact=IsPartialDict(
                            parts=[IsPartialDict(text="done: 简体")]
                        ),
                    )
                )
            )
            c_terminal = await continuation_replies.get_message()
            assert json.loads(c_terminal.payload) == IsPartialDict(
                result=IsPartialDict(
                    statusUpdate=IsPartialDict(
                        taskId=a2a_request.task_id,
                        status=IsPartialDict(state="TASK_STATE_COMPLETED"),
                    )
                )
            )

            assert interrupting_responder.requests == [a2a_request]
            assert [r.text for r in interrupting_responder.continuations] == ["简体"]

            # A new message on the terminal task is refused.
            new_request = A2ARequest(
                text="another job",
                request_id=f"new-{a2a_request.request_id}",
                task_id=a2a_request.task_id,
                context_id=a2a_request.context_id,
            )
            new_correlation = f"{correlation_id}-new".encode()
            await mqtt_client.publish(
                topics.request(agent_id),
                new_request.to_json(),
                qos=QoS.AT_LEAST_ONCE,
                properties=PublishProperties(
                    response_topic=new_topic,
                    correlation_data=new_correlation,
                ),
            )
            refused = await new_replies.get_message()
            assert refused.properties is not None
            assert refused.properties.correlation_data == new_correlation
            assert json.loads(refused.payload) == IsPartialDict(
                error=IsPartialDict(
                    code=-32602,
                    message=(
                        f"Task {a2a_request.task_id} already ended (completed) "
                        f"and accepts no further messages"
                    ),
                )
            )

        responder_task.cancel()
        with pytest.raises(asyncio.CancelledError):
            await responder_task


@pytest.mark.e2e
async def test_responder_cancels_interrupted_task(
    interrupting_responder: InterruptingResponder,
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
        responder_task = responder_runner.start(interrupting_responder)
        await presence.get_message()

        async with (
            mqtt_client.subscribe(
                reply_topic,
                qos=QoS.AT_LEAST_ONCE,
            ) as replies,
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
            await replies.get_message()  # submitted
            await replies.get_message()  # working
            interrupted = await replies.get_message()
            assert json.loads(interrupted.payload) == IsPartialDict(
                result=IsPartialDict(
                    statusUpdate=IsPartialDict(
                        taskId=a2a_request.task_id,
                        status=IsPartialDict(state="TASK_STATE_INPUT_REQUIRED"),
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
            canceled = await cancel_replies.get_message()
            assert canceled.properties is not None
            assert canceled.properties.correlation_data == cancel_correlation
            assert json.loads(canceled.payload) == IsPartialDict(
                id=f"cancel-{a2a_request.request_id}",
                result=IsPartialDict(
                    statusUpdate=IsPartialDict(
                        taskId=a2a_request.task_id,
                        status=IsPartialDict(state="TASK_STATE_CANCELED"),
                    )
                ),
            )
            assert interrupting_responder.requests == [a2a_request]

        responder_task.cancel()
        with pytest.raises(asyncio.CancelledError):
            await responder_task
