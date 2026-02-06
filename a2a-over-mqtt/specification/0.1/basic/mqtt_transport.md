---
title: MQTT Transport
---

# The MQTT Transport for A2A

This profile defines a broker-neutral A2A over MQTT topic model for discovery and messaging. It standardizes retained Agent Card discovery, request/reply mappings, and minimum security guidance while allowing broker-specific implementation choices.

## Terminology

The key words **MUST**, **SHOULD**, and **MAY** are to be interpreted as described in RFC 2119.

## Topic Model

### Discovery Topic

Agent Cards **MUST** be published as retained messages at:

```
a2a/v1/discovery/{org_id}/{unit_id}/{agent_id}
```

### Interaction Topics

Interaction topics **SHOULD** use:

```
a2a/v1/{method}/{org_id}/{unit_id}/{agent_id}
```

Where `{method}` is typically `request`, `reply`, or `event`.

## Discovery Behavior

1. Agents register by publishing retained Agent Cards to discovery topics.
2. Brokers **MUST** preserve retained Agent Cards for discovery subscribers.
3. Subscribers to matching discovery filters **MUST** receive retained cards per MQTT retained delivery rules.

## Request/Reply Mapping (MQTT v5)

1. Requesters **MUST** publish to `a2a/v1/request/{org_id}/{unit_id}/{agent_id}`.
2. Requesters **MUST** set MQTT 5 `Response Topic` and `Correlation Data`.
3. Responders **MUST** publish replies to the provided `Response Topic` and **MUST**
   echo `Correlation Data`.
4. Recommended reply topic pattern:
   `a2a/v1/reply/{org_id}/{unit_id}/{agent_id}/{reply_suffix}`.

## Agent Card Requirements

1. Card payloads **SHOULD** conform to the A2A Agent Card schema.
2. Broker/transport metadata **MAY** be expressed via Agent extension fields.
3. Extensions **MUST NOT** redefine core A2A semantics.

## Security Metadata and Trust

1. Agent Cards **MAY** include public key metadata (for example `jwksUri`) via extension params.
2. Brokers **MAY** reject cards having an untrusted `jwksUri`.
3. JWKS retrieval **SHOULD** use HTTPS with TLS certificate validation.

## Optional Broker-Managed Status Injection

To improve discovery liveness, a broker **MAY** inject/update status in card extension metadata:

- `status = "online"` when a registration is accepted or the agent is active
- `status = "offline"` when the agent is observed offline

If supported, this status is broker-managed and not client-authoritative. A broker **MAY** choose not to support status injection; lack of this feature **MUST NOT** break baseline profile conformance.

## Conformance Levels

### Core Conformance

An implementation is Core conformant if it supports:

1. Discovery retained topic model
2. Request/reply topic model
3. MQTT 5 reply correlation mapping (Response Topic + Correlation Data)

### Extended Conformance

An implementation is Extended conformant if it additionally supports one or more of:

1. Trusted JKU policy enforcement
2. Broker-managed status injection
3. Extended observability over request/reply/event traffic

## Future Work

1. HTTP JSON-RPC and A2A over MQTT interop
2. SSE and WebSocket transport guidance for streaming and bidirectional flows
3. Cross-broker conformance test suite and certification profile
