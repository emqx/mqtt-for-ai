# A2A-over-MQTT Python SDK

Python SDK for the [A2A-over-MQTT](../../specification/) protocol: build agents and clients that communicate via MQTT using the A2A (Agent-to-Agent) protocol.

## Install

```bash
pip install a2a-over-mqtt
```

Or with uv:

```bash
uv add a2a-over-mqtt
```

## Quick start

### Build a responder (agent)

```python
import asyncio
from a2a_over_mqtt import MqttConfig, TopicSpace, Responder, build_card, A2ARequest

class MyAgent(Responder):
    async def on_request(self, request: A2ARequest, stream) -> str:
        await stream("thinking...")
        return f"You said: {request.text}"

async def main():
    mqtt = MqttConfig(host="localhost", port=1883)
    topics = TopicSpace(org="myorg", unit="default")
    card = build_card(
        name="Echo Agent",
        description="Echoes back whatever you send",
        url="mqtt://localhost:1883",
    )

    agent = MyAgent(
        agent_id="echo",
        mqtt=mqtt,
        topics=topics,
        card=card,
    )
    await agent.run()

asyncio.run(main())
```

### Send a request (client)

```python
import asyncio
from a2a_over_mqtt import MqttConfig, TopicSpace, Requester, A2ARequest

async def main():
    mqtt = MqttConfig(host="localhost", port=1883)
    topics = TopicSpace(org="myorg", unit="default")
    requester = Requester(mqtt, topics)

    req = A2ARequest(text="Hello, agent!", request_id="req-1")
    async for kind, content in requester.stream("echo", req.to_json(), "corr-1"):
        print(f"{kind}: {content}")

asyncio.run(main())
```

## API overview

### Configuration

- **`MqttConfig(host, port, tls, username, password)`**: MQTT broker connection parameters. Frozen dataclass.
- **`TopicSpace(org, unit)`**: A2A topic namespace. Provides `.request()`, `.reply()`, `.discovery()`, `.event()` methods.

### Protocol (pure, no I/O)

- **`A2ARequest`** / **`A2AResponse`**: JSON-RPC 2.0 message types with serialization.
- **`make_status_event()`** / **`make_artifact_event()`**: Build streaming response messages.
- **`classify_reply(data)`**: Parse a reply into `(kind, content)` tuples.
- **`validate_a2a_request(payload, response_topic, correlation)`**: Validate inbound requests. Returns `A2ARequest` or `ValidationError`.

### Discovery

- **`build_card(name, description, url, ...)`**: Build a spec-conformant A2A Agent Card.
- **`parse_card(payload)`**: Parse a card from JSON bytes or string.

### High-level

- **`Requester`**: Send requests and stream replies with configurable retry/timeout.
- **`Responder`**: Abstract base class for agents. Implement `on_request()`, call `run()`. Handles the full protocol lifecycle: ack, streaming, artifact, terminal status, deduplication, cancellation, and LWT.

## Development

```bash
uv sync
uv run python -m pytest tests/ -v
```
