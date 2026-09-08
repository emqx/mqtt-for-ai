"""End-to-end tests for Responder discovery and connection lifecycle."""

import asyncio
import json

import pytest
from zmqtt import MQTTClientV5, QoS

from a2a_over_mqtt import TopicSpace
from tests.e2e.responders import EchoResponder, ResponderRunner


@pytest.mark.e2e
async def test_responder_publishes_online_and_graceful_offline_cards(
    echo_responder: EchoResponder,
    responder_runner: ResponderRunner,
    mqtt_client: MQTTClientV5,
    topics: TopicSpace,
    agent_id: str,
    agent_card: dict,
) -> None:
    async with mqtt_client.subscribe(
        topics.discovery(agent_id),
        qos=QoS.AT_LEAST_ONCE,
        retain_as_published=True,
    ) as presence:
        responder_task = responder_runner.start(echo_responder)
        online = await presence.get_message()
        assert json.loads(online.payload) == agent_card
        assert online.properties is not None
        assert dict(online.properties.user_properties) == {
            "a2a-status": "online",
            "a2a-status-source": "agent",
        }
        assert online.retain is True

        responder_task.cancel()
        with pytest.raises(asyncio.CancelledError):
            await responder_task
        offline = await presence.get_message()
        assert json.loads(offline.payload) == agent_card
        assert offline.properties is not None
        assert dict(offline.properties.user_properties) == {
            "a2a-status": "offline",
            "a2a-status-source": "agent",
        }
        assert offline.retain is True


@pytest.mark.e2e
async def test_responder_online_card_is_retained_for_late_subscriber(
    echo_responder: EchoResponder,
    responder_runner: ResponderRunner,
    mqtt_client: MQTTClientV5,
    second_mqtt_client: MQTTClientV5,
    topics: TopicSpace,
    agent_id: str,
    agent_card: dict,
) -> None:
    async with mqtt_client.subscribe(
        topics.discovery(agent_id),
        qos=QoS.AT_LEAST_ONCE,
    ) as initial_presence:
        responder_task = responder_runner.start(echo_responder)
        online = await initial_presence.get_message()
        assert online.properties is not None
        assert dict(online.properties.user_properties)["a2a-status"] == "online"

        async with second_mqtt_client.subscribe(
            topics.discovery(agent_id),
            qos=QoS.AT_LEAST_ONCE,
            retain_as_published=True,
        ) as late_presence:
            retained_online = await late_presence.get_message()
            assert json.loads(retained_online.payload) == agent_card
            assert retained_online.properties is not None
            assert dict(retained_online.properties.user_properties) == {
                "a2a-status": "online",
                "a2a-status-source": "agent",
            }
            assert retained_online.retain is True

        responder_task.cancel()
        with pytest.raises(asyncio.CancelledError):
            await responder_task


@pytest.mark.e2e
async def test_responder_lwt_publishes_offline_card_after_connection_loss(
    echo_responder: EchoResponder,
    responder_runner: ResponderRunner,
    mqtt_client: MQTTClientV5,
    takeover_client: MQTTClientV5,
    topics: TopicSpace,
    agent_id: str,
    agent_card: dict,
) -> None:
    async with mqtt_client.subscribe(
        topics.discovery(agent_id),
        qos=QoS.AT_LEAST_ONCE,
        retain_as_published=True,
    ) as presence:
        responder_runner.start(echo_responder)
        online = await presence.get_message()
        assert online.properties is not None
        assert dict(online.properties.user_properties)["a2a-status"] == "online"

        await takeover_client.connect()
        offline = await presence.get_message()
        assert json.loads(offline.payload) == agent_card
        assert offline.properties is not None
        assert dict(offline.properties.user_properties) == {
            "a2a-status": "offline",
            "a2a-status-source": "lwt",
        }
        assert offline.retain is True


@pytest.mark.e2e
@pytest.mark.xfail(
    strict=True,
    reason="Responder.run exits after connection loss instead of reconnecting",
)
async def test_responder_republishes_online_card_after_reconnect(
    echo_responder: EchoResponder,
    responder_runner: ResponderRunner,
    mqtt_client: MQTTClientV5,
    takeover_client: MQTTClientV5,
    topics: TopicSpace,
    agent_id: str,
) -> None:
    async with mqtt_client.subscribe(
        topics.discovery(agent_id),
        qos=QoS.AT_LEAST_ONCE,
    ) as presence:
        responder_task = responder_runner.start(echo_responder)
        online = await presence.get_message()
        assert online.properties is not None
        assert dict(online.properties.user_properties)["a2a-status"] == "online"

        await takeover_client.connect()
        offline = await presence.get_message()
        assert offline.properties is not None
        assert dict(offline.properties.user_properties)["a2a-status-source"] == "lwt"
        await takeover_client.disconnect()

        async with asyncio.timeout(1.0):
            reconnected = await presence.get_message()
        assert reconnected.properties is not None
        assert dict(reconnected.properties.user_properties) == {
            "a2a-status": "online",
            "a2a-status-source": "agent",
        }

        responder_task.cancel()
        with pytest.raises(asyncio.CancelledError):
            await responder_task
