# MQTT for AI

Specifications and SDKs for using MQTT as a transport layer in AI agent systems.

Documentation: [emqx.com/mqtt-for-ai](https://www.emqx.com/en/mqtt-for-ai/)

## Specifications

| Specification | Description |
|---|---|
| [A2A over MQTT](a2a-over-mqtt/) | Agent-to-Agent protocol over MQTT — agent discovery, request/reply, and event delivery |
| [MCP over MQTT](mcp-over-mqtt/) | [Model Context Protocol](https://modelcontextprotocol.io) transport layer over MQTT |
| [MQTT/RT](mqtt-rt/) | Real-time messaging bus over MQTT/UDP |
| [MQTT over QUIC](mqtt-quic/) | MQTT over QUIC transport protocol |
| [MQTT Queues & Streams](mqtt-queues-streams/) | Queue and stream abstractions for MQTT |
| [MQTT Subscription Filters](mqtt-subscription-filters/) | MQTT 5.0 subscription filter enhancements |
| [MQTT Batch Publishing](mqtt-batch-publishing/) | MQTT 5.0 batch publishing |

## SDKs

### A2A over MQTT — Python

[![PyPI](https://img.shields.io/pypi/v/a2a-over-mqtt)](https://pypi.org/project/a2a-over-mqtt/)

```bash
pip install a2a-over-mqtt
```

See the [SDK documentation](a2a-over-mqtt/sdk/python/) for usage details.

## Website Development

The documentation site is built with [VitePress](https://vitepress.dev/).

Requirements: Node.js >= 22, PNPM >= 10

```bash
pnpm install
pnpm run dev      # serve with hot reload at localhost:5173
pnpm run build    # build for production
```
