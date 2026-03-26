"""A2A Agent Card construction and parsing."""

import json


def build_card(
    *,
    name: str,
    description: str,
    url: str,
    skills: list[dict] | None = None,
    version: str = "0.1.0",
    capabilities: dict | None = None,
    input_modes: list[str] | None = None,
    output_modes: list[str] | None = None,
    extensions: list[dict] | None = None,
) -> dict:
    """Build a spec-conformant A2A Agent Card.

    If skills is None, a default single skill is generated from name/description.
    Extensions are appended to capabilities.extensions if provided.
    """
    caps = dict(capabilities) if capabilities else {}
    caps.setdefault("streaming", True)
    caps.setdefault("pushNotifications", False)

    if extensions:
        caps.setdefault("extensions", [])
        caps["extensions"].extend(extensions)

    if skills is None:
        skills = [
            {
                "id": name.lower().replace(" ", "-"),
                "name": name,
                "description": description,
            }
        ]

    return {
        "name": name,
        "description": description,
        "version": version,
        "supportedInterfaces": [
            {
                "url": url,
                "protocolBinding": "MQTTv5+JSONRPCv2",
                "protocolVersion": "1.0.0",
            }
        ],
        "capabilities": caps,
        "defaultInputModes": list(input_modes) if input_modes else ["text/plain"],
        "defaultOutputModes": list(output_modes) if output_modes else ["text/plain"],
        "skills": skills,
    }


def parse_card(payload: bytes | str) -> dict:
    """Parse an Agent Card from MQTT payload or JSON string."""
    return json.loads(payload)
