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

## Multi-turn (interrupted) tasks

A responder can pause a task instead of finishing it. Return
`RoundOutcome(TaskState.INPUT_REQUIRED, "which language?")`; no artifact and no
terminal status are published, and the task stays open. A later `SendMessage`
with the same `Task.id` and `context_id` calls `on_continue()`:

```python
from a2a_over_mqtt import Responder, RoundOutcome, TaskState


class Translator(Responder):
    async def on_request(self, request, stream):
        return RoundOutcome(TaskState.INPUT_REQUIRED, "which language?")

    async def on_continue(self, request, stream):
        return f"translated as: {request.text}"
```

The client sends the continuation as a new `A2ARequest` with the same
`task_id`/`context_id`; a new request is a new Message (a new `messageId`),
while re-serializing one request keeps its `messageId`, so a retry is
recognizable as the same Message. `TaskState.AUTH_REQUIRED` is the same shape
for credentials. `GetTask` reports the current state, and a message to a
terminal task is refused with `-32602`.

## API overview

### Configuration

- **`MqttConfig(host, port, tls, username, password)`**: MQTT broker connection parameters. Frozen dataclass.
- **`TopicSpace(org, unit)`**: A2A topic namespace. Provides `.request()`, `.reply()`, `.discovery()`, `.event()` methods.

### Protocol (pure, no I/O)

- **`A2ARequest`** / **`A2AResponse`**: JSON-RPC 2.0 message types with serialization. A request keeps one `message_id` across serializations; a continuation is a new request on the same `task_id`/`context_id`.
- **`TaskState`**: The A2A task states, including `INPUT_REQUIRED` and `AUTH_REQUIRED`.
- **`make_status_event()`** / **`make_artifact_event()`**: Build streaming response messages.
- **`classify_reply(data)`**: Parse a reply into `(kind, content)` tuples.
- **`validate_a2a_request(payload, response_topic, correlation)`**: Validate inbound requests. Returns `A2ARequest` or `ValidationError`.

### Discovery

- **`build_card(name, description, url, ...)`**: Build a spec-conformant A2A Agent Card.
- **`parse_card(payload)`**: Parse a card from JSON bytes or string.

### High-level

- **`Requester`**: Send requests and stream replies with configurable retry/timeout.
- **`RoundOutcome`**: What one round ended as — `completed`, `failed`, `rejected`, or an interrupted state that keeps the task open.
- **`Responder`**: Abstract base class for agents. Implement `on_request()` (and optionally `on_continue()`), call `run()`. Handles ack, streaming, artifact, terminal status, interrupted-task continuation, deduplication, `GetTask`, cancellation, and LWT.

## Development

```bash
uv sync
docker compose up -d --wait
uv run python -m pytest tests/ -v
docker compose down
```

The local EMQX broker listens on `localhost:1883`; its dashboard is available at
`http://localhost:18083`. To run the end-to-end test against another broker, set
`A2A_E2E_MQTT_HOST` and `A2A_E2E_MQTT_PORT`. The latter also overrides the
local Compose MQTT port; `A2A_EMQX_DASHBOARD_PORT` overrides the dashboard port.

### Build and publish

```bash
uv run python -m build
uv run twine upload dist/*
```
