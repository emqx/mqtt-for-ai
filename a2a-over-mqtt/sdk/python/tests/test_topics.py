"""Tests for A2A-over-MQTT topic builders."""

from a2a_over_mqtt.topics import TopicSpace


class TestTopicSpace:
    def test_request_topic(self):
        ts = TopicSpace(org="myorg", unit="myunit")
        assert ts.request("agent1") == "$a2a/v1/request/myorg/myunit/agent1"

    def test_discovery_topic(self):
        ts = TopicSpace(org="myorg", unit="myunit")
        assert ts.discovery("agent1") == "$a2a/v1/discovery/myorg/myunit/agent1"

    def test_discovery_wildcard(self):
        ts = TopicSpace(org="myorg", unit="myunit")
        assert ts.discovery_wildcard() == "$a2a/v1/discovery/myorg/myunit/+"

    def test_reply_topic(self):
        ts = TopicSpace(org="myorg", unit="myunit")
        assert (
            ts.reply("agent1", "session123")
            == "$a2a/v1/reply/myorg/myunit/agent1/session123"
        )

    def test_event_topic(self):
        ts = TopicSpace(org="myorg", unit="myunit")
        assert ts.event("agent1") == "$a2a/v1/event/myorg/myunit/agent1"

    def test_default_org_unit(self):
        ts = TopicSpace()
        assert ts.request("x") == "$a2a/v1/request/default/default/x"

    def test_frozen(self):
        ts = TopicSpace()
        import pytest

        with pytest.raises(AttributeError):
            ts.org = "changed"
