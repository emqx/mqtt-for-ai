import uuid
from collections.abc import AsyncIterator

import pytest
from zmqtt import MQTTClientV5, create_client

from a2a_over_mqtt import A2ARequest, MqttConfig, Requester, TopicSpace, build_card
from tests.e2e.responders import ControlledResponder, EchoResponder, ResponderRunner


@pytest.fixture
def run_id() -> str:
    return uuid.uuid4().hex


@pytest.fixture
def mqtt_config() -> MqttConfig:
    return MqttConfig(
        host="127.0.0.1",
        port=1883,
    )


@pytest.fixture
def agent_id(run_id: str) -> str:
    return f"echo-{run_id[:12]}"


@pytest.fixture
def topics(run_id: str) -> TopicSpace:
    return TopicSpace(org=f"e2e-{run_id[:12]}", unit="tests")


@pytest.fixture
def a2a_request(run_id: str) -> A2ARequest:
    return A2ARequest(
        text="hello",
        request_id=f"request-{run_id}",
        task_id=str(uuid.uuid4()),
        context_id=str(uuid.uuid4()),
    )


@pytest.fixture
def parallel_requests(run_id: str) -> tuple[A2ARequest, A2ARequest]:
    return (
        A2ARequest(
            text="first",
            request_id=f"first-{run_id}",
            task_id=str(uuid.uuid4()),
            context_id=str(uuid.uuid4()),
        ),
        A2ARequest(
            text="second",
            request_id=f"second-{run_id}",
            task_id=str(uuid.uuid4()),
            context_id=str(uuid.uuid4()),
        ),
    )


@pytest.fixture
def mismatched_context_request(
    a2a_request: A2ARequest,
    run_id: str,
) -> A2ARequest:
    return A2ARequest(
        text=a2a_request.text,
        request_id=f"mismatch-{run_id}",
        task_id=a2a_request.task_id,
        context_id=f"different-context-{run_id}",
    )


@pytest.fixture
def correlation_id(run_id: str) -> str:
    return f"correlation-{run_id}"


@pytest.fixture
def parallel_correlation_ids(run_id: str) -> tuple[str, str]:
    return f"first-correlation-{run_id}", f"second-correlation-{run_id}"


@pytest.fixture
def reply_topic(topics: TopicSpace, run_id: str) -> str:
    return topics.reply("test-requester", run_id)


@pytest.fixture
def agent_card(mqtt_config: MqttConfig, agent_id: str) -> dict:
    return build_card(
        name="E2E Echo Agent",
        description="Echoes E2E requests",
        url=f"mqtt://{mqtt_config.host}:{mqtt_config.port}",
    )


@pytest.fixture
def echo_responder(
    mqtt_config: MqttConfig,
    topics: TopicSpace,
    agent_id: str,
    agent_card: dict,
) -> EchoResponder:
    return EchoResponder(
        agent_id=agent_id,
        mqtt=mqtt_config,
        topics=topics,
        card=agent_card,
    )


@pytest.fixture
def controlled_responder(
    mqtt_config: MqttConfig,
    topics: TopicSpace,
    agent_id: str,
    agent_card: dict,
) -> ControlledResponder:
    return ControlledResponder(
        agent_id=agent_id,
        mqtt=mqtt_config,
        topics=topics,
        card=agent_card,
    )


@pytest.fixture
async def responder_runner() -> AsyncIterator[ResponderRunner]:
    runner = ResponderRunner()
    try:
        yield runner
    finally:
        await runner.close()


@pytest.fixture
def requester(mqtt_config: MqttConfig, topics: TopicSpace, run_id: str) -> Requester:
    return Requester(
        mqtt_config,
        topics,
        requester_id=f"requester-{run_id[:12]}",
        first_reply_timeout=10.0,
        stream_idle_timeout=10.0,
        max_attempts=1,
    )


@pytest.fixture
def timeout_requester(
    mqtt_config: MqttConfig,
    topics: TopicSpace,
    run_id: str,
) -> Requester:
    return Requester(
        mqtt_config,
        topics,
        requester_id=f"timeout-{run_id[:12]}",
        first_reply_timeout=0.2,
        stream_idle_timeout=0.2,
        max_attempts=1,
    )


@pytest.fixture
def retrying_requester(
    mqtt_config: MqttConfig,
    topics: TopicSpace,
    run_id: str,
) -> Requester:
    return Requester(
        mqtt_config,
        topics,
        requester_id=f"retry-{run_id[:12]}",
        first_reply_timeout=0.1,
        stream_idle_timeout=1.0,
        max_attempts=2,
    )


@pytest.fixture
async def mqtt_client(
    mqtt_config: MqttConfig,
    topics: TopicSpace,
    run_id: str,
) -> AsyncIterator[MQTTClientV5]:
    async with create_client(
        mqtt_config.host,
        mqtt_config.port,
        client_id=f"{topics.org}/{topics.unit}/test-peer-{run_id[:8]}",
        version="5.0",
    ) as client:
        yield client


@pytest.fixture
async def second_mqtt_client(
    mqtt_config: MqttConfig,
    topics: TopicSpace,
    run_id: str,
) -> AsyncIterator[MQTTClientV5]:
    async with create_client(
        mqtt_config.host,
        mqtt_config.port,
        client_id=f"{topics.org}/{topics.unit}/second-peer-{run_id[:8]}",
        version="5.0",
    ) as client:
        yield client


@pytest.fixture
async def takeover_client(
    mqtt_config: MqttConfig,
    topics: TopicSpace,
    agent_id: str,
) -> AsyncIterator[MQTTClientV5]:
    client = create_client(
        mqtt_config.host,
        mqtt_config.port,
        client_id=f"{topics.org}/{topics.unit}/{agent_id}",
        version="5.0",
    )
    try:
        yield client
    finally:
        await client.disconnect()
