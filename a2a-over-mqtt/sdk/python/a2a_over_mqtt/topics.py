"""A2A-over-MQTT topic scheme."""

from dataclasses import dataclass

_PREFIX = "$a2a/v1"


@dataclass(frozen=True)
class TopicSpace:
    """Namespace for A2A-over-MQTT topic construction.

    All topic methods produce strings following the A2A-over-MQTT v0.1 topic
    scheme: ``$a2a/v1/{category}/{org}/{unit}/{agent_id}``.
    """

    org: str = "default"
    unit: str = "default"

    def discovery(self, agent_id: str) -> str:
        """Retained Agent Card: $a2a/v1/discovery/{org}/{unit}/{agent_id}"""
        return f"{_PREFIX}/discovery/{self.org}/{self.unit}/{agent_id}"

    def discovery_wildcard(self) -> str:
        """Wildcard for all discovery cards: $a2a/v1/discovery/{org}/{unit}/+"""
        return f"{_PREFIX}/discovery/{self.org}/{self.unit}/+"

    def request(self, agent_id: str) -> str:
        """Request topic: $a2a/v1/request/{org}/{unit}/{agent_id}"""
        return f"{_PREFIX}/request/{self.org}/{self.unit}/{agent_id}"

    def reply(self, agent_id: str, suffix: str) -> str:
        """Reply topic: $a2a/v1/reply/{org}/{unit}/{agent_id}/{suffix}"""
        return f"{_PREFIX}/reply/{self.org}/{self.unit}/{agent_id}/{suffix}"

    def event(self, agent_id: str) -> str:
        """Event topic: $a2a/v1/event/{org}/{unit}/{agent_id}"""
        return f"{_PREFIX}/event/{self.org}/{self.unit}/{agent_id}"
