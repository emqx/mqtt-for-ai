---
title: MQTT Transport
a2a_spec_version: "1.0.0"
a2a_spec_ref: "https://github.com/a2aproject/A2A/tree/v1.0.0"
---

# The MQTT Transport for A2A

This profile defines a broker-neutral A2A over MQTT topic model for discovery and messaging. It standardizes retained Agent Card discovery, request/reply mappings, request-scoped security metadata, and interoperable client behavior.

> **A2A base specification:** This profile extends the [A2A specification v1.0.0](https://github.com/a2aproject/A2A/tree/v1.0.0). All normative A2A data structures, method semantics, and error codes are as defined in that release unless explicitly overridden by this profile.

## Profile Scope

1. This profile specifies MQTT v5 topic conventions and message-property mappings for [A2A v1.0.0](https://github.com/a2aproject/A2A/tree/v1.0.0) traffic.
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
$a2a/v1/discovery/{org_id}/{unit_id}/{agent_id}
```

### Direct Interaction Topics

Interaction topics **SHOULD** use:

```
$a2a/v1/{method}/{org_id}/{unit_id}/{agent_id}
```

Where `{method}` is typically `request`, `reply`, or `event`.

### Optional Pool Request Topic

Shared pool dispatch uses:

```
$a2a/v1/request/{org_id}/{unit_id}/pool/{pool_id}
```

## Identifier Format

1. Identifiers used in this profile (`org_id`, `unit_id`, `agent_id`, `pool_id`, and `group_id`) **MUST** match:
   - `^[A-Za-z0-9_.-]+$`

## Client Session Requirements

1. Clients implementing this profile **MUST** use MQTT v5.
2. Requesters **MUST** subscribe to the intended reply topic before publishing requests that use that topic as MQTT `Response Topic`.
3. Clients **MUST** set MQTT `Client ID` in the format `{org_id}/{unit_id}/{agent_id}`.
4. Requesters **SHOULD** use a reply topic suffix with high collision resistance (`reply_suffix`) so concurrent requesters do not overlap reply streams.
5. Clients **SHOULD** use reconnect behavior that preserves subscriptions/session state where broker policy allows.
6. Connections carrying bearer tokens **MUST** use TLS.

## Discovery Interoperability

1. Agent Cards **MAY** be discovered via HTTP well-known endpoints defined by core A2A conventions.
2. For MQTT-compliant agents, publishing retained Agent Cards to `$a2a/v1/discovery/{org_id}/{unit_id}/{agent_id}` is **RECOMMENDED**.
3. A client **MAY** discover a card via HTTP and then choose MQTT by selecting an MQTT-capable entry from `supportedInterfaces`.

## Discovery Publisher Behavior

1. Agents register by publishing retained Agent Cards to discovery topics and **SHOULD** use MQTT QoS 1.
2. To unregister, agents **SHOULD** clear retained discovery state using the broker-supported retained-delete mechanism for the same topic.
3. Agents updating cards **SHOULD** republish the full card payload for that topic.

## Discovery Subscriber Behavior

1. Discovery subscribers **SHOULD** subscribe using scoped filters such as:
   - `$a2a/v1/discovery/{org_id}/{unit_id}/+`
2. Subscribers **MUST** process retained discovery messages as current registration state.
3. Subscribers **SHOULD** treat subsequent retained updates on the same discovery topic as replacement state for that agent.
4. Subscribers **MAY** combine HTTP-discovered cards and MQTT-discovered cards, but topic-scoped MQTT cards are authoritative for MQTT routing.
5. Subscribers **SHOULD** process the MQTT User Property `a2a-status` on received Agent Card messages to determine agent liveness. See [Presence and Liveness](#presence-and-liveness).

## Presence and Liveness

Agent Cards are published as retained messages and persist on the broker after an agent disconnects. This section defines how agents signal operational status using MQTT User Properties on Agent Card publications, so that subscribers can distinguish a reachable agent from a stale card.

### Liveness via Discovery Topic User Properties

Agents signal liveness by attaching MQTT v5 User Properties to their retained Agent Card publications on the discovery topic. Subscribers receive capability metadata and operational status in a single retained message.

1. Agents **SHOULD** include MQTT User Property `a2a-status` with value `online` when publishing their retained Agent Card.
2. Agents **SHOULD** include MQTT User Property `a2a-status-source` with value `agent` on Agent Card publications to distinguish agent-published status from broker-managed status.

### Last Will and Testament (LWT) Configuration

1. Agents **SHOULD** configure an MQTT Last Will and Testament (LWT) at connection time:
   - Will Topic: `$a2a/v1/discovery/{org_id}/{unit_id}/{agent_id}` (same as the agent's discovery topic)
   - Will Payload: the Agent Card JSON payload
   - Will Retain: `true`
   - Will QoS: `1`
   - Will User Properties: `a2a-status=offline`, `a2a-status-source=lwt`
2. On ungraceful disconnect (crash, network loss), the broker publishes the LWT, replacing the retained card with an offline-annotated version. Subscribers are notified automatically.
3. On graceful disconnect, agents **SHOULD** republish their retained Agent Card with User Properties `a2a-status=offline` and `a2a-status-source=agent` before disconnecting, providing immediate notification without waiting for the broker's keep-alive timeout.
4. The LWT payload is fixed at CONNECT time. If an agent updates its card during a session, the LWT will carry the previous card version. The `a2a-status=offline` signal remains valid; subscribers receive the updated card when the agent reconnects and republishes.
5. This profile relies on MQTT keep-alive for connection-level liveness detection. The broker declares a client dead after 1.5× the negotiated Keep Alive interval with no PINGREQ, which triggers the LWT. Application-level heartbeat mechanisms (for example, Message Expiry Interval on retained cards) are not specified in this version; they may be defined in a future revision if MQTT keep-alive proves insufficient.

### Presence Subscriber Behavior

1. Subscribers **SHOULD** process the MQTT User Property `a2a-status` on received Agent Card messages. A value of `online` indicates the agent was reachable when the card was published; `offline` indicates a disconnect was detected.
2. Subscribers **MUST** treat `a2a-status` as advisory and **MUST NOT** use it as a replacement for request/reply error handling and retry behavior.
3. Subscribers **SHOULD** interpret the absence of a retained Agent Card (no message on the discovery topic) as the agent being unregistered or unavailable.
4. A subscriber that needs definitive liveness confirmation for a specific agent before committing to a costly operation **MAY** send a lightweight request (for example `GetTask` with a non-existent `Task.id`) and use the reply timeout as a health signal.

## Request/Reply Mapping (MQTT v5)

1. Requesters **SHOULD** publish requests to `$a2a/v1/request/{org_id}/{unit_id}/{agent_id}` using MQTT QoS 1.
2. Requesters **MUST** set MQTT 5 `Response Topic` and `Correlation Data`.
3. Responders **MUST** publish replies to the provided `Response Topic` and **MUST**
   echo `Correlation Data`. Replies **SHOULD** be published using MQTT QoS 1.
4. Recommended reply topic pattern:
   `$a2a/v1/reply/{org_id}/{unit_id}/{agent_id}/{reply_suffix}`.
5. MQTT `Correlation Data` is transport-level request/reply correlation and **MUST NOT** be used as an A2A task identifier.
6. For new tasks, requesters **MUST** generate a `Task.id` as a UUIDv4 value and include it in the request payload (`Message.task_id`).
   > **MQTT binding divergence:** The core A2A specification states that `Task.id` is generated by the server (responder). This binding intentionally reverses that: the requester generates `Task.id` before sending the first request. This is necessary over MQTT because there is no synchronous response — the requester must be able to retry the initial publish (with a new `Correlation Data`) without the risk of the responder creating a duplicate task.
7. Responders **MUST** use the requester-provided `Task.id` (`Message.task_id`) to track task state and **MUST** echo it in all replies and stream items for that task.
8. Requesters **MUST** use the same `Task.id` for all subsequent task operations (for example `GetTask`, `CancelTask`, and subscriptions).
9. Requesters **MAY** include a `Task.context_id` in the request payload (`Message.context_id`) to group related tasks into a conversational session. See [Multi-Turn Conversation Patterns](#multi-turn-conversation-patterns).

### Informative: Why Both Correlation Data and Task.id

This section is informative (non-normative).

MQTT `Correlation Data` and A2A `Task.id` serve complementary but distinct roles:

| Identifier | Scope | Generated by | Lifetime |
| --- | --- | --- | --- |
| `Correlation Data` | Single MQTT request/reply exchange | Requester (per publish) | One round-trip |
| `Task.id` (`Message.task_id`) | Logical task / conversation session | Requester (UUIDv4, on task creation) | Entire task lifecycle |

Both are necessary because:

1. **Separate lifetimes.** `Task.id` is a stable UUIDv4 generated by the requester at task creation and reused for the entire task lifecycle. `Correlation Data` is ephemeral — a new value is generated for each individual MQTT publish, including retries.
2. **Multiple in-flight requests per task.** Over one task session a requester may send several concurrent requests (for example `SendMessage` followed by `GetTask`). Each needs its own `Correlation Data` so replies can be demultiplexed independently.
3. **MQTT does not guarantee cross-topic ordering.** Unlike HTTP pipelining, where intermediaries preserve message order within a connection, MQTT message delivery order is non-deterministic when messages traverse different topic suffixes. `Correlation Data` lets requesters match replies regardless of arrival order.
4. **Retry deduplication.** Because `Task.id` is requester-generated and present from the first request, responders can use it to deduplicate retried task-creating requests (where the first attempt was processed but the reply was lost).

Typical lifecycle:

1. Requester generates a UUIDv4 `Task.id` and publishes the initial `SendMessage` request (`SendMessageRequest`) with both `Message.task_id` (in the payload) and `Correlation Data` (MQTT property).
2. Responder accepts the task, persists state keyed by `Task.id`, and replies (echoing `Correlation Data`).
3. Requester uses the same `Task.id` for all subsequent task operations, generating fresh `Correlation Data` for each new publish.

> See also [Multi-Turn Conversation Patterns](#multi-turn-conversation-patterns) for the third identifier tier — `Task.context_id`.

## Requester Behavior (Interop)

1. Requesters **MUST** keep an in-flight map keyed by MQTT `Correlation Data` for active requests.
2. `Correlation Data` values **MUST** be unique across concurrently in-flight requests from that requester on the same reply topic.
3. Requesters **SHOULD** publish requests with QoS 1.
4. Requesters **MUST** include request-scoped auth properties (for example `a2a-authorization`) when required by the target responder.
5. On reply, requesters **MUST** match `Correlation Data`; replies with unknown or missing correlation **MUST** be treated as protocol errors and ignored.
6. For pooled requests, requesters **MUST** validate presence of `a2a-responder-agent-id` on pooled responses; missing property **MUST** be treated as a protocol error.
7. For pooled requests that create or reference a task, requesters **MUST** persist (`Task.id`, `a2a-responder-agent-id`).
8. Follow-up task operations (`GetTask`, `CancelTask`, subsequent stream/task interactions) **SHOULD** be routed to direct responder topics once responder identity is known.
9. Requesters **MUST** implement the retry and timeout behavior defined in `Requester Retry and Timeout Profile`.

## Responder Behavior (Interop)

1. Responders **MUST** subscribe to their direct request topic and **MAY** additionally subscribe to pool request topics when operating in shared dispatch mode.
2. If a request omits `Response Topic` or `Correlation Data`, responders **SHOULD** reject it as invalid protocol input; if no reply path is available, responders **MAY** drop.
3. Responders **MUST** validate request payloads and return protocol/application errors on the provided reply path when possible.
4. For new tasks, responders **MUST** accept the requester-provided `Task.id` (a UUIDv4 value) and use it to track task state. Responders **MUST** reject requests with missing or malformed `Task.id` as invalid protocol input.
5. Responders **MUST** echo `Correlation Data` unchanged on all replies and stream items for a request.
6. Replies and stream items **SHOULD** be sent with QoS 1.
7. Responders processing pooled requests **MUST** include User Property `a2a-responder-agent-id` on responses.
8. Responders **MUST NOT** echo bearer tokens in payloads or MQTT properties.

## Optional Task Handover

1. A card-owning agent **MAY** delegate an in-progress task to a different agent instance. This allows a single published Agent Card to front multiple dynamically spawned or specialized agent instances without requiring each instance to register its own card.
2. To signal handover, the responding agent **MUST** include MQTT User Property `a2a-responder-agent-id` on the reply, with the value set to the delegated agent's `agent_id`. This reuses the same property defined for shared pool dispatch.
3. When a requester receives a reply containing `a2a-responder-agent-id`, it **SHOULD** direct all subsequent operations for that `Task.id` to the indicated agent's direct request topic. This behavior is the same regardless of whether the property originates from pool dispatch or task handover.
4. The property **MAY** appear on any reply or stream message for a given task. Requesters **MUST** honor the most recently received `a2a-responder-agent-id` for a given `Task.id`.
5. Handover does not alter the task's identity; `Task.id` remains the same across the handover.
6. If the card-owning agent does not hand over, it is responsible for correctly routing incoming messages to its internal instances (for example by session or `Task.id`). How an agent manages its internal instances is implementation-specific and out of scope.

## Multi-Turn Conversation Patterns

This section defines how the A2A `Task.context_id` maps to the MQTT transport binding for conversational continuity across multiple tasks and interrupted-task flows.

> **A2A base specification alignment:** This section maps the multi-turn conversation patterns defined in [A2A specification v1.0.0 §3.4.3](https://a2a-protocol.org/latest/specification/#343-multi-turn-conversation-patterns) to MQTT transport semantics.

### Context Identifier Semantics

1. A `Task.context_id` logically groups related tasks and messages into a single conversational session.
2. Requesters **SHOULD** generate a `Task.context_id` as a UUIDv4 value and include it in the request payload (`Message.context_id`) when initiating a new conversation.
   > **MQTT binding note:** Consistent with the requester-generated `Task.id` model, requesters generate `Task.context_id` before sending. Requesters that do not include `Task.context_id` are opting out of conversational continuity for that task.
3. If the request payload omits `Task.context_id`, the responder **MAY** generate one and include it in the response task object.
4. Responders **MUST** preserve and echo the requester-provided `Task.context_id` in all responses for tasks within that context.
5. If a responder receives a `Task.context_id` with no existing associated state, it **MUST** treat it as the start of a new conversational context.
6. Responders **MUST** reject requests where the incoming `Task.context_id` differs from the `Task.context_id` already associated with the same `Task.id` in the responder's stored task state. The error **MUST** use JSON-RPC error code `-32602` (invalid params).
7. Requesters **MAY** include MQTT User Property `a2a-context-id` with the `Task.context_id` value on request publications for transport-level visibility. The JSON payload `Message.context_id` remains authoritative; if both are present, they **MUST** match.
8. All tasks sharing a `Task.context_id` constitute a single conversational session. Responders **MAY** maintain internal state or LLM context across interactions within the same context.
9. Responders **MAY** implement context expiration policies; such policies **SHOULD** be documented in the Agent Card or agent metadata.

### Interaction Patterns

Multi-turn conversations combine three identifier tiers:

| Identifier | Scope | Generated by | Lifetime |
| --- | --- | --- | --- |
| `Task.context_id` (`Message.context_id`) | Conversation | Requester (UUIDv4) | Multiple tasks |
| `Task.id` (`Message.task_id`) | Task | Requester (UUIDv4) | Entire task lifecycle |
| `Correlation Data` | Request/reply exchange | Requester (per publish) | One round-trip |

1. **New conversation.** Requester generates a new `Task.context_id` (UUIDv4) and a new `Task.id` (UUIDv4), publishes `SendMessage` with fresh `Correlation Data`.
2. **New turn in existing conversation.** Requester generates a new `Task.id` but reuses the existing `Task.context_id`, publishes with fresh `Correlation Data`. Responders **MAY** leverage prior task history within the same context to inform processing.
3. **Continue interrupted task.** When a responder transitions a task to `input-required` or `auth-required`, the requester publishes a new `SendMessage` with the **same** `Task.id` and `Task.context_id` and fresh `Correlation Data`. The responder resumes processing on the new correlation. See [Streaming Reply Mapping](#streaming-reply-mapping-sendstreamingmessage) for stream-final semantics of interrupted states.
4. **Retry.** Requester reuses the same `Task.id` and `Task.context_id` with new `Correlation Data`, as defined in [Requester Retry and Timeout Profile](#requester-retry-and-timeout-profile).

## Requester Retry and Timeout Profile

1. This section defines the baseline retry/timeout behavior for requester interoperability and is part of Core conformance.
2. Requesters **MUST** implement these defaults (configurable by deployment policy):
   - `reply_first_timeout_ms`: `15000`
   - `stream_idle_timeout_ms`: `30000`
   - `max_attempts`: `3` total attempts (initial attempt plus up to two retries)
   - `retry_backoff_ms`: exponential (`1000`, `2000`, `4000`) with jitter of `+/-20%`
3. For a single logical operation retried multiple times, requesters **MUST** generate new MQTT `Correlation Data` for each publish attempt and **MUST** keep the same `Task.id` in the payload.
4. Responders **MUST** use `Task.id` to deduplicate retried requests. If a responder has already created state for a given `Task.id`, it **MUST** return the existing task state rather than creating a duplicate.
5. Requesters **MUST** stop retrying after the first valid correlated reply is received (success or error).
6. Requesters **MUST** treat these conditions as retry-eligible until `max_attempts` is reached:
   - publish not accepted by the MQTT client/broker path
   - request timed out waiting for first correlated reply (`reply_first_timeout_ms`)
7. Once any correlated stream item is received, requesters **MUST NOT** retry the original request publish.
8. If stream progress stalls longer than `stream_idle_timeout_ms` after at least one stream item, requesters **SHOULD** recover using task follow-up (`GetTask`) with the known `Task.id` instead of republishing the original request.
9. For pooled requests:
   - retries before responder selection **MUST** target the pool topic
   - after responder identity is known (`a2a-responder-agent-id`), follow-up operations and retries **MUST** target that responder's direct request topic
10. Requesters **MAY** set MQTT Message Expiry Interval on request publications; if set, it **SHOULD** be greater than `reply_first_timeout_ms`.

## Optional Shared Subscription Dispatch

1. This profile supports an optional unit-scoped shared dispatch mode so compatible responders (same contract/intent) can share request load while keeping standard A2A request/reply behavior.
2. Canonical shared pool request topic:
   - `$a2a/v1/request/{org_id}/{unit_id}/pool/{pool_id}`
3. Requesters **MUST** publish pooled tasks to the canonical non-shared pool request topic and **MUST NOT** publish directly to `$share/...`.
4. Pool members **MAY** consume pooled requests via:
   - `$share/{group_id}/$a2a/v1/request/{org_id}/{unit_id}/pool/{pool_id}`
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
    - `$a2a/v1/request/{org_id}/{unit_id}/{agent_id}`
12. A designated agent in the unit **MAY** act as pool registrar and publish/update metadata describing `pool_id`, membership, and the pool request topic.
13. How pool members coordinate membership, liveness, leader election, and failover is implementation-specific and out of scope for this profile.
14. Shared dispatch is intentionally limited to `{org_id}/{unit_id}` scope in this version because unit boundaries map to common tenancy/policy boundaries; cross-unit or org-global shared pools are not defined.

## Streaming Reply Mapping (`SendStreamingMessage`)

1. For streaming A2A operations, responders **MUST** publish each stream item as a discrete MQTT message to the request-provided `Response Topic`.
2. Each stream message **MUST** echo the same MQTT 5 `Correlation Data` as the originating request.
3. Stream payloads **SHOULD** use A2A stream update structures, including `TaskStatusUpdateEvent` and `TaskArtifactUpdateEvent`.
4. Stream updates **SHOULD** be published using MQTT QoS 1 so publishers can receive PUBACK reason codes (for example, `No matching subscribers`).
5. For this MQTT binding, receipt of a `TaskStatusUpdateEvent.status.state` value of `TASK_STATE_COMPLETED`, `TASK_STATE_FAILED`, `TASK_STATE_CANCELED`, or `TASK_STATE_REJECTED` **MUST** be treated as the end of that stream for the given correlation.
6. Requesters **MUST** treat that terminal status as stream completion for the correlated request.
7. A `TaskStatusUpdateEvent` with `status.state` of `input-required` or `auth-required` **MUST** also be treated as stream-final for the current correlation: the requester **MUST** clean up in-flight state for that `Correlation Data`. The task is not terminal — see [Multi-Turn Conversation Patterns](#multi-turn-conversation-patterns) for continuation behavior.
8. If a requester does not receive terminal status within its stream timeout policy, it **MAY** issue follow-up task retrieval (`GetTask`) using `Task.id`.
9. This end-of-stream rule applies to reply-stream messages on the request/reply path, not to general-purpose `$a2a/v1/event/...` publications.

## Event Delivery

1. Event messages published to `$a2a/v1/event/{org_id}/{unit_id}/{agent_id}` **MAY** use MQTT QoS 0.
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

## Optional Untrusted-Broker Security Profile

1. This profile defines an optional end-to-end payload protection mode for environments where broker/topic ACLs are not sufficient to guarantee confidentiality.
2. Profile identifier:
   - MQTT User Property key: `a2a-security-profile`
   - value: `ubsp-v1`
3. When `a2a-security-profile=ubsp-v1` is set on a request, requester and responder **MUST** use end-to-end encrypted payloads for all request, reply, and stream messages for that interaction.
4. Under `ubsp-v1`, payloads **MUST** use JOSE JWE serialization:
   - MQTT `Content Type` **MUST** be `application/jose+json` (JSON serialization) or `application/jose` (compact serialization).
5. Requesters **MUST** encrypt request payloads to the target responder public key resolved from trusted agent metadata (for example Agent Card extensions such as `jwksUri`, or trusted OIDC/OAuth metadata links).
6. Responders **MUST** encrypt reply/stream payloads to the requester public key resolved from trusted metadata.
7. Requesters using `ubsp-v1` **MUST** provide discoverable public key metadata so responders can resolve a reply encryption key.
8. Under `ubsp-v1`, request publications **MUST** include MQTT User Properties:
   - key: `a2a-security-profile`, value: `ubsp-v1`
   - key: `a2a-requester-agent-id`, value: requester `agent_id`
   - key: `a2a-recipient-agent-id`, value: intended responder `agent_id`
9. Under `ubsp-v1`, response publications **MUST** include MQTT User Properties:
   - key: `a2a-security-profile`, value: `ubsp-v1`
   - key: `a2a-requester-agent-id`, value: requester `agent_id`
   - key: `a2a-responder-agent-id`, value: responder `agent_id`
10. Implementations **MAY** include `a2a-recipient-kid` to indicate the JWK `kid` used for encryption.
11. Responders **MUST** verify that `a2a-recipient-agent-id` matches local responder identity before processing a `ubsp-v1` request; mismatches **MUST** be rejected as `transport_protocol_error`.
12. Requesters and responders using `ubsp-v1` **SHOULD** enforce replay protection for protected payloads (for example `jti` and short-lived `exp` claims in protected content).
13. This profile reduces payload confidentiality/integrity dependency on broker ACL correctness, but does not replace transport TLS, authentication, or authorization requirements in this specification.

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
     - key: `a2a-context-id`, value: `Task.context_id` value
9. MQTT User Property values are UTF-8 strings; non-string metadata **MUST** be string-encoded.
10. Native binary artifact messages **SHOULD** use MQTT QoS 1.
11. `a2a-last-chunk=true` indicates artifact chunk completion only; stream completion semantics still follow terminal task status (`TASK_STATE_COMPLETED`, `TASK_STATE_FAILED`, `TASK_STATE_CANCELED`).

## Optional Broker-Managed Status via MQTT User Properties

As a complement to agent-published liveness (see [Presence and Liveness](#presence-and-liveness)), a broker **MAY** override or attach MQTT v5 User Properties on retained discovery messages when forwarding them to subscribers.

1. Brokers implementing this feature **SHOULD** set or override the following User Properties based on the agent's MQTT client connection state:
   - key: `a2a-status`, value: `online` when the agent's client connection is active
   - key: `a2a-status`, value: `offline` when the agent's client connection is observed disconnected
   - key: `a2a-status-source`, value: `broker` to indicate the status originates from broker connection tracking (replacing any agent-published `a2a-status-source` value)
2. Brokers **SHOULD** derive status from the agent's MQTT client connection state, keyed by Client ID (`{org_id}/{unit_id}/{agent_id}`).
3. Subscribers **MUST** treat broker-managed status properties as advisory transport metadata and **MUST NOT** treat them as a replacement for request/reply error handling.
4. When `a2a-status-source=broker` is present, subscribers **SHOULD** prefer it over agent-published status for connection-level reachability, as the broker has authoritative knowledge of TCP connection state.

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
7. Multi-turn conversation patterns (`Task.context_id` semantics and interrupted-task continuation)
8. Presence and liveness (LWT configuration, `a2a-status` User Property on Agent Card publications)

### Extended Conformance

An implementation is Extended conformant if it additionally supports one or more of:

1. Trusted JKU policy enforcement
2. Broker-managed status via MQTT User Properties
3. Extended observability over request/reply/event traffic
4. Native binary artifact mode over MQTT
5. Shared-subscription request dispatch
6. Untrusted-broker security profile (`ubsp-v1`)

## Future Work

1. HTTP JSON-RPC and A2A over MQTT interop
2. SSE and WebSocket transport guidance for streaming and bidirectional flows
3. Cross-broker conformance test suite and certification profile
