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

## Discovery Interoperability

1. Agent Cards **MAY** be discovered via HTTP well-known endpoints defined by core A2A conventions.
2. For MQTT-compliant agents, publishing retained Agent Cards to `a2a/v1/discovery/{org_id}/{unit_id}/{agent_id}` is **RECOMMENDED**.
3. A client **MAY** discover a card via HTTP and then choose MQTT by selecting an MQTT-capable entry from `supportedInterfaces`.

## Discovery Behavior

1. Agents register by publishing retained Agent Cards to discovery topics and **SHOULD** use MQTT QoS 1.
2. Brokers **MUST** preserve retained Agent Cards for discovery subscribers.
3. Subscribers to matching discovery filters **MUST** receive retained cards per MQTT retained delivery rules.

## Request/Reply Mapping (MQTT v5)

1. Requesters **SHOULD** publish to `a2a/v1/request/{org_id}/{unit_id}/{agent_id}` using MQTT QoS 1.
2. Requesters **MUST** set MQTT 5 `Response Topic` and `Correlation Data`.
3. Responders **MUST** publish replies to the provided `Response Topic` and **MUST**
   echo `Correlation Data`. Replies **SHOULD** be published using MQTT QoS 1.
4. Recommended reply topic pattern:
   `a2a/v1/reply/{org_id}/{unit_id}/{agent_id}/{reply_suffix}`.

## Streaming Reply Mapping (`message/stream`)

1. For streaming A2A operations, responders **MUST** publish each stream item as a discrete MQTT message to the request-provided `Response Topic`.
2. Each stream message **MUST** echo the same MQTT 5 `Correlation Data` as the originating request.
3. Stream payloads **SHOULD** use A2A stream update structures, including `TaskStatusUpdateEvent` and `TaskArtifactUpdateEvent`.
4. Stream updates **SHOULD** be published using MQTT QoS 1 so publishers can receive PUBACK reason codes (for example, `No matching subscribers`).
5. For this MQTT binding, receipt of a `TaskStatusUpdateEvent.status.state` value of `TASK_STATE_COMPLETED`, `TASK_STATE_FAILED`, or `TASK_STATE_CANCELED` **MUST** be treated as the end of that stream for the given correlation.
6. This end-of-stream rule applies to reply-stream messages on the request/reply path, not to general-purpose `a2a/v1/event/...` publications.

## Event Delivery

1. Event messages published to `a2a/v1/event/{org_id}/{unit_id}/{agent_id}` **MAY** use MQTT QoS 0.

## QoS Guidance

1. MQTT QoS 1 is the recommended default for discovery registration, request, and reply publications.
2. Using QoS 1 allows publishers to receive MQTT v5 PUBACK responses that can carry broker reason codes, for example `No matching subscribers`.
3. Brokers and clients **MUST** support QoS 1 on discovery, request, and reply paths for interoperability.

## A2A User Property Naming

1. MQTT User Properties defined by this binding **MUST** use the `a2a-` prefix.
2. New binding-specific properties defined by implementations **SHOULD** also use the `a2a-` prefix to avoid collisions.

## Agent Card Requirements

1. Card payloads **SHOULD** conform to the A2A Agent Card schema.
2. Agent-provided transport metadata **MAY** be expressed via Agent extension fields.
3. Extensions **MUST NOT** redefine core A2A semantics.

## Security Metadata and Trust

1. Agent Cards **MAY** include public key metadata (for example `jwksUri`) via extension params.
2. Brokers **MAY** reject cards having an untrusted `jwksUri`.
3. JWKS retrieval **SHOULD** use HTTPS with TLS certificate validation.

## OAuth 2.0 and OIDC over MQTT User Properties

1. OAuth 2.0/OIDC token acquisition is out-of-band for this binding and occurs between the requester and an authorization server.
2. If the selected agent requires OAuth 2.0/OIDC, the requester **MUST** include an access token on each request message as an MQTT v5 User Property:
   - key: `a2a-authorization`
   - value: `Bearer <access_token>`
3. Broker connection authentication (for example username/password or mTLS) is independent of per-request OAuth authorization and **MUST NOT** be treated as a replacement for it.
4. Responders **MUST** validate bearer token claims (including `exp`, `iss`, and `aud`) and required scopes before processing the request.
5. Request messages carrying bearer tokens **MUST** be sent over TLS-secured MQTT transport.
6. Implementations **MUST NOT** echo bearer tokens in reply/event payloads or MQTT properties; implementations **SHOULD** redact such values from logs and telemetry.

## Optional MQTT Native Binary Artifact Mode

1. Baseline interoperability remains JSON payloads, where binary `Part.raw` content is represented using base64 in JSON serialization.
2. Implementations **MAY** support an optional native binary artifact mode for high-throughput scenarios.
3. Mode selection for artifact encoding is controlled by request MQTT User Property `a2a-artifact-mode`.
4. Requesters **MAY** set `a2a-artifact-mode` to one of:
   - `json` (default, JSON-compatible artifact payloads)
   - `binary` (native MQTT binary artifact payloads)
5. If `a2a-artifact-mode=binary` is requested and supported by the responder, the responder **MAY** publish artifact chunks as raw binary payloads on the reply stream topic.
6. If `a2a-artifact-mode` is absent, unknown, or unsupported by the responder, implementations **MUST** use `json` mode.
7. Responders **SHOULD** indicate the chosen mode in reply messages using MQTT User Property:
   - key: `a2a-artifact-mode`
   - value: `json` or `binary`
8. Each native binary artifact message **MUST**:
   - echo the request `Correlation Data`
   - set MQTT Payload Format Indicator to `0` (unspecified bytes)
   - use MQTT Content Type when artifact media type is known
   - include MQTT User Properties:
     - key: `a2a-event-type`, value: `task-artifact-update`
     - key: `a2a-task-id`, value: task identifier
     - key: `a2a-artifact-id`, value: artifact identifier
     - key: `a2a-chunk-seqno`, value: chunk sequence number
     - key: `a2a-last-chunk`, value: `true` or `false`
   - optionally include:
     - key: `a2a-context-id`, value: context identifier
9. MQTT User Property values are UTF-8 strings; non-string metadata **MUST** be string-encoded.
10. Native binary artifact messages **SHOULD** use MQTT QoS 1.
11. `a2a-last-chunk=true` indicates artifact chunk completion only; stream completion semantics still follow terminal task status (`TASK_STATE_COMPLETED`, `TASK_STATE_FAILED`, `TASK_STATE_CANCELED`).

## Optional Broker-Managed Status via MQTT User Properties

To improve discovery liveness, a broker **MAY** attach MQTT v5 User Properties when forwarding discovery messages to subscribers.

Recommended properties:

- key: `a2a-status`, value: `"online"` when a registration is accepted or the agent is active
- key: `a2a-status`, value: `"offline"` when the agent is observed offline
- key: `a2a-status-source`, value: `"broker"` to indicate transport-level broker status

## Conformance Levels

### Core Conformance

An implementation is Core conformant if it supports:

1. Discovery retained topic model
2. Request/reply topic model
3. MQTT 5 reply correlation mapping (Response Topic + Correlation Data)
4. QoS interoperability support: MQTT QoS 1 on discovery, request, and reply paths

### Extended Conformance

An implementation is Extended conformant if it additionally supports one or more of:

1. Trusted JKU policy enforcement
2. Broker-managed status via MQTT User Properties
3. Extended observability over request/reply/event traffic
4. Native binary artifact mode over MQTT

## Future Work

1. HTTP JSON-RPC and A2A over MQTT interop
2. SSE and WebSocket transport guidance for streaming and bidirectional flows
3. Cross-broker conformance test suite and certification profile
