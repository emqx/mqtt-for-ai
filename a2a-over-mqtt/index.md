---
title: A2A over MQTT
---

# A2A over MQTT

This is the specification and reference materials for A2A over MQTT, a broker-neutral profile for agent discovery and messaging.

## Why MQTT?

MQTT is a lightweight and widely used protocol for IoT and edge computing. It is designed for unreliable networks and low bandwidth, making it a good choice for distributed agent systems that need discovery and message delivery across constrained links.

Introducing MQTT as a transport for A2A enables agent discovery via retained messages, broker-neutral request/reply conventions, and interoperable event delivery across systems that already use MQTT.

## Features

The A2A over MQTT profile defines:

- **Interoperable Agent Discovery**: retained Agent Cards at a standardized discovery topic.
- **Request/Reply Topic Conventions**: consistent mapping for request, reply, and event topics.
- **Minimal Security Guidance**: optional trust metadata for Agent Cards without mandating broker internals.

## Limitations

This profile is broker-neutral by design. It does not standardize broker internal architecture, UI, or administrative APIs. It also does not define end-to-end application semantics beyond the topic model and discovery behavior.
