"""Tests for A2A Agent Card construction and parsing."""

import json

from a2a_over_mqtt.discovery import build_card, parse_card


class TestBuildCard:
    def test_defaults(self):
        card = build_card(
            name="Researcher",
            description="Deep research with citations",
            url="mqtt://broker:1883",
        )
        assert card["name"] == "Researcher"
        assert card["description"] == "Deep research with citations"
        assert card["version"] == "0.1.0"
        assert "url" not in card
        ifaces = card["supportedInterfaces"]
        assert len(ifaces) == 1
        assert ifaces[0]["protocolVersion"] == "1.0.0"
        assert ifaces[0]["protocolBinding"] == "MQTTv5+JSONRPCv2"
        assert ifaces[0]["url"] == "mqtt://broker:1883"
        assert card["capabilities"]["streaming"] is True
        assert card["capabilities"]["pushNotifications"] is False
        assert card["defaultInputModes"] == ["text/plain"]
        assert card["defaultOutputModes"] == ["text/plain"]
        assert len(card["skills"]) == 1
        assert card["skills"][0]["id"] == "researcher"
        assert card["skills"][0]["name"] == "Researcher"

    def test_custom_capabilities(self):
        card = build_card(
            name="Coder",
            description="Writes code",
            url="mqtt://broker:1883",
            capabilities={"streaming": False},
            input_modes=["text/plain", "application/json"],
        )
        assert card["capabilities"]["streaming"] is False
        assert card["capabilities"]["pushNotifications"] is False
        assert card["defaultInputModes"] == ["text/plain", "application/json"]

    def test_custom_skills(self):
        skills = [
            {
                "id": "s1",
                "name": "Skill One",
                "description": "Does things",
                "tags": ["a", "b"],
            }
        ]
        card = build_card(
            name="Agent",
            description="Desc",
            url="mqtt://x:1883",
            skills=skills,
        )
        assert card["skills"] == skills

    def test_extensions(self):
        ext = [{"uri": "urn:custom:ext", "params": {"key": "val"}}]
        card = build_card(
            name="Agent",
            description="Desc",
            url="mqtt://x:1883",
            extensions=ext,
        )
        assert card["capabilities"]["extensions"] == ext

    def test_custom_url(self):
        card = build_card(
            name="Test",
            description="Test agent",
            url="mqtt://custom:1883",
        )
        assert card["supportedInterfaces"][0]["url"] == "mqtt://custom:1883"

    def test_default_skill_id_from_name(self):
        card = build_card(
            name="My Cool Agent",
            description="Does cool things",
            url="mqtt://x:1883",
        )
        assert card["skills"][0]["id"] == "my-cool-agent"


class TestParseCard:
    def test_parse_bytes(self):
        raw = json.dumps({"name": "Test", "version": "0.1.0"}).encode()
        card = parse_card(raw)
        assert card["name"] == "Test"

    def test_parse_string(self):
        raw = json.dumps({"name": "Agent"})
        card = parse_card(raw)
        assert card["name"] == "Agent"
