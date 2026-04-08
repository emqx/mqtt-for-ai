"""MQTT v5 transport: config, connection kwargs, property helpers."""

import ssl
from dataclasses import dataclass

import aiomqtt
from paho.mqtt.packettypes import PacketTypes
from paho.mqtt.properties import Properties


@dataclass(frozen=True)
class MqttConfig:
    """MQTT broker connection parameters."""

    host: str = "localhost"
    port: int = 1883
    tls: bool = False
    username: str = ""
    password: str = ""

    def client_kwargs(self, **overrides) -> dict:
        """Build kwargs dict for ``aiomqtt.Client(**config.client_kwargs())``."""
        kwargs: dict = {
            "hostname": self.host,
            "port": self.port,
            "protocol": aiomqtt.ProtocolVersion.V5,
        }
        if self.tls:
            kwargs["tls_context"] = ssl.create_default_context()
        if self.username:
            kwargs["username"] = self.username
            kwargs["password"] = self.password
        kwargs.update(overrides)
        return kwargs


# --- MQTT v5 property helpers ---


def make_properties(
    response_topic: str | None = None,
    correlation_data: str | None = None,
) -> Properties:
    """Build MQTT v5 PUBLISH properties with Response Topic and/or Correlation Data."""
    props = Properties(PacketTypes.PUBLISH)
    if response_topic:
        props.ResponseTopic = response_topic
    if correlation_data:
        props.CorrelationData = correlation_data.encode("utf-8")
    return props


def get_correlation_data(msg) -> str | None:
    """Extract Correlation Data from an aiomqtt message (v5 properties)."""
    props = getattr(msg, "properties", None)
    if props is None:
        return None
    cd = getattr(props, "CorrelationData", None)
    if cd is None:
        return None
    return cd.decode("utf-8") if isinstance(cd, (bytes, bytearray)) else str(cd)


def get_response_topic(msg) -> str | None:
    """Extract Response Topic from an aiomqtt message (v5 properties)."""
    props = getattr(msg, "properties", None)
    if props is None:
        return None
    return getattr(props, "ResponseTopic", None)
