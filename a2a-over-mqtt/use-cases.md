# Use Cases

A2A over MQTT is suitable for distributed agent systems that need broker-neutral discovery and reliable request/reply messaging. Typical scenarios include:

- **Cross-team agent catalogs**: multiple teams publish retained Agent Cards so clients can discover agents by org/unit/agent identifiers.
- **Edge and on-prem agent coordination**: sites with intermittent connectivity can use MQTT retained discovery and lightweight messaging.
- **Event-driven agent workflows**: standardized `event` topics allow agents to emit and subscribe to lifecycle or status events.
