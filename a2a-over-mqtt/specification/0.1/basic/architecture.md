---
title: Architecture
---

# Architecture

## Core Components

A2A over MQTT introduces a broker-centric transport model while keeping agent semantics unchanged:

```mermaid
graph LR
    subgraph "Clients"
        C1[Client]
    end

    subgraph "MQTT Broker"
        B[Broker]
    end

    subgraph "Agents"
        A1[Agent]
        A2[Agent]
    end

    C1 --> B
    A1 --> B
    A2 --> B
```

### Agents

Agents publish a retained **Agent Card** to a discovery topic. The card describes the agent and may include optional trust metadata.

### Clients

Clients subscribe to discovery topics to find agents and publish requests to request topics. Replies are returned on corresponding reply topics.

### MQTT Broker

The broker routes discovery, request/reply, and event messages. It may optionally enforce trust policies for Agent Cards or inject broker-managed status metadata, but those choices are implementation-specific and not required for core conformance.
