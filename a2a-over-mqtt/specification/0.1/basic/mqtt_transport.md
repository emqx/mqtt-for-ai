---
title: MQTT Transport
---

# The MQTT Transport for A2A

This profile defines a broker-neutral A2A over MQTT topic model for discovery and messaging. It standardizes retained Agent Card discovery, request/reply mappings, request-scoped security metadata, and interoperable client behavior.

## Profile Scope

1. This profile specifies MQTT v5 topic conventions and message-property mappings for A2A traffic.
2. This profile defines interoperable behavior for requester clients and responder clients.
3. Broker-internal implementation details remain implementation-specific unless explicitly stated.

## Terminology

The key words **MUST**, **SHOULD**, and **MAY** are to be interpreted as described in RFC 2119.

Additional terms used in this profile:

- `requester`: client agent that publishes A2A requests
- `responder`: client agent that consumes requests and publishes replies
- `discovery subscriber`: client that subscribes to discovery topics
- `pool`: optional unit-scoped shared request endpoint consumed via MQTT shared subscriptions

## Topic Model

### Discovery Topic

Agent Cards **MUST** be published as retained messages at:

```
a2a/v1/discovery/{org_id}/{unit_id}/{agent_id}
```

### Direct Interaction Topics

Interaction topics **SHOULD** use:

```
a2a/v1/{method}/{org_id}/{unit_id}/{agent_id}
```

Where `{method}` is typically `request`, `reply`, or `event`.

### Optional Pool Request Topic

Shared pool dispatch uses:

```
a2a/v1/request/{org_id}/{unit_id}/pool/{pool_id}
```

## Identifier Format

1. Identifiers used in this profile (`org_id`, `unit_id`, `agent_id`, `pool_id`, and `group_id`) **MUST** match:
   - `^[A-Za-z0-9._]+$`
2. Identifiers **MUST NOT** contain `/`, `+`, `#`, whitespace, or any character outside the set above.

## Client Session Requirements

1. Clients implementing this profile **MUST** use MQTT v5.
2. Requesters **MUST** subscribe to the intended reply topic before publishing requests that use that topic as MQTT `Response Topic`.
3. Request/reply/event publications defined by this profile **MUST NOT** be retained.
4. Requesters **SHOULD** use a reply topic suffix with high collision resistance (`reply_suffix`) so concurrent requesters do not overlap reply streams.
5. Clients **SHOULD** use reconnect behavior that preserves subscriptions/session state where broker policy allows.
6. Connections carrying bearer tokens **MUST** use TLS.

## Discovery Interoperability

1. Agent Cards **MAY** be discovered via HTTP well-known endpoints defined by core A2A conventions.
2. For MQTT-compliant agents, publishing retained Agent Cards to `a2a/v1/discovery/{org_id}/{unit_id}/{agent_id}` is **RECOMMENDED**.
3. A client **MAY** discover a card via HTTP and then choose MQTT by selecting an MQTT-capable entry from `supportedInterfaces`.

## Discovery Publisher Behavior

1. Agents register by publishing retained Agent Cards to discovery topics and **SHOULD** use MQTT QoS 1.
2. To unregister, agents **SHOULD** clear retained discovery state using the broker-supported retained-delete mechanism for the same topic.
3. Agents updating cards **SHOULD** republish the full card payload for that topic.

## Discovery Subscriber Behavior

1. Discovery subscribers **SHOULD** subscribe using scoped filters such as:
   - `a2a/v1/discovery/{org_id}/{unit_id}/+`
2. Subscribers **MUST** process retained discovery messages as current registration state.
3. Subscribers **SHOULD** treat subsequent retained updates on the same discovery topic as replacement state for that agent.
4. Subscribers **MAY** combine HTTP-discovered cards and MQTT-discovered cards, but topic-scoped MQTT cards are authoritative for MQTT routing.

## Request/Reply Mapping (MQTT v5)

1. Requesters **SHOULD** publish requests to `a2a/v1/request/{org_id}/{unit_id}/{agent_id}` using MQTT QoS 1.
2. Requesters **MUST** set MQTT 5 `Response Topic` and `Correlation Data`.
3. Responders **MUST** publish replies to the provided `Response Topic` and **MUST**
   echo `Correlation Data`. Replies **SHOULD** be published using MQTT QoS 1.
4. Recommended reply topic pattern:
   `a2a/v1/reply/{org_id}/{unit_id}/{agent_id}/{reply_suffix}`.
5. MQTT `Correlation Data` is transport-level request/reply correlation and **MUST NOT** be used as an A2A task identifier.
6. For newly created tasks, responders **MUST** return a server-generated A2A `Task.id` in the response payload.
7. Requesters **MUST** use that returned `Task.id` for subsequent task operations (for example `tasks/get`, `tasks/cancel`, and subscriptions).

## Requester Behavior (Interop)

1. Requesters **MUST** keep an in-flight map keyed by MQTT `Correlation Data` for active requests.
2. `Correlation Data` values **MUST** be unique across concurrently in-flight requests from that requester on the same reply topic.
3. Requesters **SHOULD** publish requests with QoS 1 and **MUST NOT** set retained.
4. Requesters **MUST** include request-scoped auth properties (for example `a2a-authorization`) when required by the target responder.
5. On reply, requesters **MUST** match `Correlation Data`; replies with unknown or missing correlation **MUST** be treated as protocol errors and ignored.
6. For pooled requests, requesters **MUST** validate presence of `a2a-responder-agent-id` on pooled responses; missing property **MUST** be treated as a protocol error.
7. If a response creates or references a task, requesters **MUST** persist `Task.id`; for pooled requests they **MUST** persist (`Task.id`, `a2a-responder-agent-id`).
8. Follow-up task operations (`tasks/get`, `tasks/cancel`, subsequent stream/task interactions) **SHOULD** be routed to direct responder topics once responder identity is known.
9. Requesters **MUST** implement the retry and timeout behavior defined in `Requester Retry and Timeout Profile`.

## Responder Behavior (Interop)

1. Responders **MUST** subscribe to their direct request topic and **MAY** additionally subscribe to pool request topics when operating in shared dispatch mode.
2. If a request omits `Response Topic` or `Correlation Data`, responders **SHOULD** reject it as invalid protocol input; if no reply path is available, responders **MAY** drop.
3. Responders **MUST** validate request payloads and return protocol/application errors on the provided reply path when possible.
4. For new tasks, responders **MUST** generate `Task.id` server-side and return it in the response payload.
5. Responders **MUST** echo `Correlation Data` unchanged on all replies and stream items for a request.
6. Replies and stream items **SHOULD** be sent with QoS 1 and **MUST NOT** be retained.
7. Responders processing pooled requests **MUST** include User Property `a2a-responder-agent-id` on responses.
8. Responders **MUST NOT** echo bearer tokens in payloads or MQTT properties.

## Requester Retry and Timeout Profile

1. This section defines the baseline retry/timeout behavior for requester interoperability and is part of Core conformance.
2. Requesters **MUST** implement these defaults (configurable by deployment policy):
   - `reply_first_timeout_ms`: `15000`
   - `stream_idle_timeout_ms`: `30000`
   - `max_attempts`: `3` total attempts (initial attempt plus up to two retries)
   - `retry_backoff_ms`: exponential (`1000`, `2000`, `4000`) with jitter of `+/-20%`
3. For a single logical operation retried multiple times, requesters **MUST** keep the same A2A/JSON-RPC request id and **MUST** generate new MQTT `Correlation Data` for each publish attempt.
4. Requesters **MUST** stop retrying after the first valid correlated reply is received (success or error).
5. Requesters **MUST** treat these conditions as retry-eligible until `max_attempts` is reached:
   - publish not accepted by the MQTT client/broker path
   - request timed out waiting for first correlated reply (`reply_first_timeout_ms`)
6. Once any correlated stream item is received, requesters **MUST NOT** retry the original request publish.
7. If stream progress stalls longer than `stream_idle_timeout_ms` after at least one stream item, requesters **SHOULD** recover using task follow-up (`tasks/get`) with the known `Task.id` instead of republishing the original request.
8. For pooled requests:
   - retries before responder selection **MUST** target the pool topic
   - after responder identity is known (`a2a-responder-agent-id`), follow-up operations and retries **MUST** target that responder's direct request topic
9. Requesters **MAY** set MQTT Message Expiry Interval on request publications; if set, it **SHOULD** be greater than `reply_first_timeout_ms`.

## Optional Shared Subscription Dispatch

1. This profile supports an optional unit-scoped shared dispatch mode so compatible responders (same contract/intent) can share request load while keeping standard A2A request/reply behavior.
2. Canonical shared pool request topic:
   - `a2a/v1/request/{org_id}/{unit_id}/pool/{pool_id}`
3. Requesters **MUST** publish pooled tasks to the canonical non-shared pool request topic and **MUST NOT** publish directly to `$share/...`.
4. Pool members **MAY** consume pooled requests via:
   - `$share/{group_id}/a2a/v1/request/{org_id}/{unit_id}/pool/{pool_id}`
5. All members of the same `{org_id}/{unit_id}/{pool_id}` pool **MUST** use the same `group_id`.
6. `group_id` **SHOULD** be deterministic and stable. Recommended base value:
   - `a2a.{org_id}.{unit_id}.{pool_id}`
7. If an implementation derives `group_id` from external labels, it **SHOULD** replace characters outside `[A-Za-z0-9._]` with `_` before use.
8. Implementations **MUST NOT** use random per-instance values (for example UUIDs) as `group_id`.
9. Implementations **SHOULD** enforce broker length limits for `group_id` (recommended max `64`); if needed, truncate and append a short hash suffix.
10. A responder handling a pooled request **MUST** include MQTT User Property:
    - key: `a2a-responder-agent-id`
    - value: concrete responder `agent_id`
11. For pooled requests that create tasks, requesters **SHOULD** persist (`Task.id`, `a2a-responder-agent-id`) and **SHOULD** route follow-up operations to the concrete responder direct request topic:
    - `a2a/v1/request/{org_id}/{unit_id}/{agent_id}`
12. A designated agent in the unit **MAY** act as pool registrar and publish/update metadata describing `pool_id`, membership, and the pool request topic.
13. How pool members coordinate membership, liveness, leader election, and failover is implementation-specific and out of scope for this profile.
14. Shared dispatch is intentionally limited to `{org_id}/{unit_id}` scope in this version because unit boundaries map to common tenancy/policy boundaries; cross-unit or org-global shared pools are not defined.

## Streaming Reply Mapping (`message/stream`)

1. For streaming A2A operations, responders **MUST** publish each stream item as a discrete MQTT message to the request-provided `Response Topic`.
2. Each stream message **MUST** echo the same MQTT 5 `Correlation Data` as the originating request.
3. Stream payloads **SHOULD** use A2A stream update structures, including `TaskStatusUpdateEvent` and `TaskArtifactUpdateEvent`.
4. Stream updates **SHOULD** be published using MQTT QoS 1 so publishers can receive PUBACK reason codes (for example, `No matching subscribers`).
5. For this MQTT binding, receipt of a `TaskStatusUpdateEvent.status.state` value of `TASK_STATE_COMPLETED`, `TASK_STATE_FAILED`, or `TASK_STATE_CANCELED` **MUST** be treated as the end of that stream for the given correlation.
6. Requesters **MUST** treat that terminal status as stream completion for the correlated request.
7. If a requester does not receive terminal status within its stream timeout policy, it **MAY** issue follow-up task retrieval (`tasks/get`) using `Task.id`.
8. This end-of-stream rule applies to reply-stream messages on the request/reply path, not to general-purpose `a2a/v1/event/...` publications.

## Event Delivery

1. Event messages published to `a2a/v1/event/{org_id}/{unit_id}/{agent_id}` **MAY** use MQTT QoS 0.
2. Event publications are outside request/reply correlation unless explicitly tied by application metadata.

## QoS Guidance

1. MQTT QoS 1 is the recommended default for discovery registration, request, and reply publications.
2. Using QoS 1 allows publishers to receive MQTT v5 PUBACK responses that can carry broker reason codes, for example `No matching subscribers`.
3. Brokers and clients **MUST** support QoS 1 on discovery, request, and reply paths for interoperability.
4. Event publications **MAY** use QoS 0 when occasional loss is acceptable.

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
6. Implementations **MUST NOT** echo bearer tokens in reply/event payloads or MQTT properties.
7. Requesters **SHOULD** refresh/replace expired tokens before retrying protected requests.

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

Subscribers **MUST** treat these status properties as advisory transport metadata and **MUST NOT** treat them as replacement for card payload semantics.

## Error Handling and Deduplication

1. Requesters and responders **MUST** tolerate duplicate delivery behavior possible with MQTT QoS 1.
2. Requesters **SHOULD** de-duplicate stream/reply items using available keys, such as `Correlation Data`, `a2a-task-id`, `a2a-artifact-id`, and `a2a-chunk-seqno`.
3. Unknown `a2a-` User Properties **SHOULD** be ignored unless marked mandatory by this profile.
4. Implementations **MAY** use MQTT Message Expiry Interval for stale-request control.
5. If message expiry indicates the request is stale before processing, responders **SHOULD** drop it and **MAY** publish an expiration-related error when a valid reply path exists.

## Mandatory Binding-Specific Error Mapping (JSON-RPC over MQTT)

1. Error replies on MQTT request/reply paths **MUST** use JSON-RPC `error` objects.
2. Error replies **MUST** echo the request MQTT `Correlation Data`.
3. For generic JSON-RPC and A2A method/application errors (for example parse, invalid request, method not found, invalid params, authn/authz failures), implementations **MUST** follow the core A2A/JSON-RPC definitions.
4. This MQTT binding defines the following mandatory transport-specific mapping:

| Condition | JSON-RPC `error.code` | `error.data.a2a_error` |
| --- | --- | --- |
| Request expired before processing | `-32003` | `request_expired` |
| Temporary responder unavailable/overloaded | `-32004` | `responder_unavailable` |
| MQTT binding protocol metadata invalid | `-32005` | `transport_protocol_error` |

5. For `-32003` to `-32005`, responders **MUST** include `error.data.a2a_error` exactly as shown above.
6. `transport_protocol_error` covers invalid or missing MQTT binding metadata required by this profile (for example malformed or missing request/reply binding properties).
7. Requesters **MUST** treat `-32003` and `-32004` as retry-eligible at application policy level; transport-layer retries still follow `Requester Retry and Timeout Profile`.
8. Requesters **MUST** treat `-32005` as non-retryable unless request metadata is corrected.

## Conformance Levels

### Core Conformance

An implementation is Core conformant if it supports:

1. Discovery retained topic model
2. Request/reply topic model
3. MQTT 5 reply correlation mapping (Response Topic + Correlation Data)
4. Requester and responder interop behavior defined in this profile
5. QoS interoperability support: MQTT QoS 1 on discovery, request, and reply paths
6. Mandatory error-code mapping defined in this profile

### Extended Conformance

An implementation is Extended conformant if it additionally supports one or more of:

1. Trusted JKU policy enforcement
2. Broker-managed status via MQTT User Properties
3. Extended observability over request/reply/event traffic
4. Native binary artifact mode over MQTT
5. Shared-subscription request dispatch

## Future Work

1. HTTP JSON-RPC and A2A over MQTT interop
2. SSE and WebSocket transport guidance for streaming and bidirectional flows
3. Cross-broker conformance test suite and certification profile
