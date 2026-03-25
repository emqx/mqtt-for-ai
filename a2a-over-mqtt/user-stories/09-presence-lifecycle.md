# User Story 09: Presence Lifecycle

Implementation-oriented user story for SDK development.

## Agent Presence Through Connect, Disconnect, and Crash Scenarios

### Goal

An agent publishes its Agent Card with liveness status so that discovery subscribers can determine whether the agent is currently reachable. The lifecycle covers initial registration, graceful disconnect, reconnect, and crash recovery via LWT.

### Preconditions

- Agent B uses Client ID `{org_id}/{unit_id}/{agent_b_id}`.
- Agent B has an Agent Card JSON payload ready to publish.
- Discovery Subscriber S is subscribed to:
  - `$a2a/v1/discovery/{org_id}/{unit_id}/+`

### End-to-End Flow

#### Phase 1: Initial Connection (online, source=agent)

1. Agent B connects to the broker with:
   - Client ID: `{org_id}/{unit_id}/{agent_b_id}`
   - LWT configured:
     - Will Topic: `$a2a/v1/discovery/{org_id}/{unit_id}/{agent_b_id}`
     - Will Payload: Agent Card JSON
     - Will Retain: `true`
     - Will QoS: `1`
     - Will User Properties: `a2a-status=offline`, `a2a-status-source=lwt`
2. Agent B publishes its retained Agent Card:
   - Topic: `$a2a/v1/discovery/{org_id}/{unit_id}/{agent_b_id}`
   - Retain: `true`
   - QoS: `1`
   - User Properties: `a2a-status=online`, `a2a-status-source=agent`
   - Payload: Agent Card JSON
3. Subscriber S receives the retained card with `a2a-status=online`, `a2a-status-source=agent`.
4. Subscriber S records Agent B as online and available.

#### Phase 2: Graceful Disconnect (offline, source=agent)

1. Agent B prepares to shut down.
2. Agent B publishes its retained Agent Card with offline status:
   - Topic: `$a2a/v1/discovery/{org_id}/{unit_id}/{agent_b_id}`
   - Retain: `true`
   - QoS: `1`
   - User Properties: `a2a-status=offline`, `a2a-status-source=agent`
   - Payload: Agent Card JSON
3. Agent B disconnects cleanly. The broker does not fire the LWT.
4. Subscriber S receives the updated retained card with `a2a-status=offline`, `a2a-status-source=agent`.
5. Subscriber S records Agent B as offline (graceful shutdown).

#### Phase 3: Reconnect (online, source=agent)

1. Agent B reconnects to the broker with the same Client ID and LWT configuration as Phase 1.
2. Agent B publishes its retained Agent Card with `a2a-status=online`, `a2a-status-source=agent`.
3. Subscriber S receives the updated retained card with `a2a-status=online`.
4. Subscriber S records Agent B as online again.

#### Phase 4: Crash / Ungraceful Disconnect (offline, source=lwt)

1. Agent B loses connectivity or crashes. No graceful disconnect occurs.
2. After 1.5x the negotiated Keep Alive interval with no PINGREQ, the broker declares Agent B's session dead.
3. The broker publishes the LWT:
   - Topic: `$a2a/v1/discovery/{org_id}/{unit_id}/{agent_b_id}`
   - Retain: `true`
   - QoS: `1`
   - User Properties: `a2a-status=offline`, `a2a-status-source=lwt`
   - Payload: Agent Card JSON (as set at CONNECT time)
4. Subscriber S receives the retained card with `a2a-status=offline`, `a2a-status-source=lwt`.
5. Subscriber S records Agent B as offline (ungraceful, LWT-triggered).

### Phase 5: Broker-Managed Status (Optional, Extended Conformance)

When the broker implements optional broker-managed status (see spec: Optional Broker-Managed Status via MQTT User Properties), it **MAY** attach or set `a2a-status` and `a2a-status-source` User Properties on retained discovery messages when forwarding them to subscribers. This works independently of agent-published status — the agent does not need to implement LWT or publish `a2a-status` itself for broker-managed status to function.

#### 5a: Broker Detects Connect (online, source=broker)

1. Agent B connects (or reconnects) to the broker.
2. The broker detects a new client session for Client ID `{org_id}/{unit_id}/{agent_b_id}`.
3. When forwarding the retained Agent Card to subscribers, the broker attaches:
   - `a2a-status=online`, `a2a-status-source=broker`
4. Subscriber S receives the card with `a2a-status=online`, `a2a-status-source=broker`.
5. Subscriber S records Agent B as online (broker-confirmed).

#### 5b: Broker Detects Disconnect (offline, source=broker)

1. Agent B disconnects (gracefully or ungracefully).
2. The broker detects the client session for `{org_id}/{unit_id}/{agent_b_id}` is closed.
3. When forwarding the retained Agent Card to subscribers, the broker attaches:
   - `a2a-status=offline`, `a2a-status-source=broker`
4. Subscriber S receives the card with `a2a-status=offline`, `a2a-status-source=broker`.
5. Subscriber S records Agent B as offline (broker-confirmed).

> **Note:** When `a2a-status-source=broker` is present, subscribers SHOULD prefer it over agent-published or LWT-published status, as the broker has authoritative knowledge of TCP connection state.

### Subscriber State Machine

| Event received | `a2a-status` | `a2a-status-source` | Subscriber interpretation |
| --- | --- | --- | --- |
| Card published | `online` | `agent` | Agent is reachable |
| Card republished | `offline` | `agent` | Agent shut down gracefully |
| LWT fired | `offline` | `lwt` | Agent crashed or lost connection |
| Broker-managed | `online` | `broker` | Broker confirms agent connected |
| Broker-managed | `offline` | `broker` | Broker confirms agent disconnected |
| No retained card | — | — | Agent unregistered or unavailable |

### SDK Requirements Checklist

- On connect: configure LWT with the Agent Card payload and `a2a-status=offline`, `a2a-status-source=lwt` User Properties.
- On connect: publish retained Agent Card with `a2a-status=online`, `a2a-status-source=agent`.
- On graceful disconnect: publish retained Agent Card with `a2a-status=offline`, `a2a-status-source=agent` before calling disconnect.
- Subscriber: parse `a2a-status` and `a2a-status-source` User Properties on all received discovery messages.
- Subscriber: maintain per-agent status keyed by `{agent_id}` extracted from the topic.
- Subscriber: when `a2a-status-source=broker` is present, prefer it over `agent` or `lwt` sourced status.
- Subscriber: treat `a2a-status` as advisory; do not skip request/reply retry logic based on status alone.

### Failure Cases to Test

- Agent crashes before publishing the initial card: LWT fires with the card payload; subscriber sees the agent as offline (never saw online).
- Agent updates its card mid-session then crashes: LWT carries the old card version but `a2a-status=offline` is still valid. On reconnect, agent publishes the current card.
- Broker restarts: retained messages may be lost depending on broker persistence configuration. Subscriber should handle absence of retained card gracefully.
- Subscriber connects after agent crash and LWT: subscriber receives the LWT-published retained card with `a2a-status=offline`.
