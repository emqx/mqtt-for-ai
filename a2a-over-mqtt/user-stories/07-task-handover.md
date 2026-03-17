# User Story 07: Task Handover

Implementation-oriented user story for SDK development.

## Card Agent Delegates Task to a Spawned Agent Instance

### Goal

Agent A sends a request to a card-owning agent (Agent B). Agent B accepts the request, delegates the task to a spawned or specialized agent instance (Agent C), and signals the handover so Agent A routes follow-up operations directly to Agent C.

### Preconditions

- Agent B is discoverable on:
  - `$a2a/v1/discovery/{org_id}/{unit_id}/{agent_b_id}`
- Agent C is a spawned instance managed by Agent B. Agent C does not publish its own Agent Card but has a distinct Client ID (`{org_id}/{unit_id}/{agent_c_id}`).
- Agent A has a subscribed reply topic and can publish to Agent B's request topic.

### End-to-End Flow

1. Agent A subscribes to reply topic:
   - `$a2a/v1/reply/{org_id}/{unit_id}/{agent_a_id}/{reply_suffix}`
2. Agent A publishes request to Agent B:
   - `$a2a/v1/request/{org_id}/{unit_id}/{agent_b_id}`
   - MQTT v5 properties:
     - `Response Topic`: reply topic above
     - `Correlation Data`: unique request correlation bytes
   - Payload includes requester-generated `Task.id` (UUIDv4)
3. Agent B receives the request, accepts the `Task.id`, and decides to delegate to Agent C.
4. Agent B (or Agent C on behalf of Agent B) publishes reply to `Response Topic`:
   - Echoes the same `Correlation Data`
   - Includes User Property:
     - key: `a2a-responder-agent-id`
     - value: `{agent_c_id}`
   - Payload echoes `Task.id`
5. Agent A persists:
   - `Task.id`
   - Responder agent: `{org_id}/{unit_id}/{agent_c_id}`
6. Agent A sends follow-up task operations to Agent C's direct request topic:
   - `$a2a/v1/request/{org_id}/{unit_id}/{agent_c_id}`

### SDK Requirements Checklist

- Parse `a2a-responder-agent-id` User Property on any reply or stream message.
- Update task routing table when handover is received: subsequent operations for that `Task.id` target the new agent.
- Honor the most recently received `a2a-responder-agent-id` if multiple are received for the same `Task.id`.
- `Task.id` does not change across handover.
- Generate new `Correlation Data` for follow-up requests to the handover target.

### Failure Cases to Test

- Responder agent unreachable: requester applies retry profile against the new agent's direct topic; if exhausted, requester may fall back to the original card agent.
- Missing `a2a-responder-agent-id` on reply: requester continues routing to the original card agent (no handover).
- Multiple handovers in a streaming session: requester honors the latest `a2a-responder-agent-id` value.
