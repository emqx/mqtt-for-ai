# User Story 05: Shared Pool Dispatch

Implementation-oriented user story for SDK development.

## One Request to Unit Pool, One Responder Selected by Shared Subscription

### Goal

Agent A sends a request to a unit-level shared pool topic. Multiple compatible agents are subscribed through a shared subscription group, and exactly one responder agent handles the request.

### Preconditions

- Compatible responder agents are registered under the same unit and support the same service contract.
- Responders subscribe with the same shared group:
  - `$share/{group_id}/$a2a/v1/request/{org_id}/{unit_id}/pool/{pool_id}`
- Agent A has a subscribed reply topic and can publish to the pool request topic.

### End-to-End Flow

1. Agent A publishes request to:
   - `$a2a/v1/request/{org_id}/{unit_id}/pool/{pool_id}`
   - QoS: `1` (recommended)
   - MQTT v5 properties:
     - `Response Topic`: `$a2a/v1/reply/{org_id}/{unit_id}/{client_agent_id}/{reply_suffix}`
     - `Correlation Data`: unique request correlation bytes
2. Broker delivers the request to one responder in the shared group.
3. Selected responder processes request and publishes reply to `Response Topic`:
   - echoes same `Correlation Data`
   - includes User Property:
     - key: `a2a-responder-agent-id`
     - value: concrete responder `agent_id`
4. If a task is created, reply includes server-generated `Task.id`.
5. Agent A records tuple:
   - `Task.id`
   - `a2a-responder-agent-id`
6. Agent A sends follow-up task operations to the concrete responder direct topic:
   - `$a2a/v1/request/{org_id}/{unit_id}/{a2a-responder-agent-id}`

### SDK Requirements Checklist

- Support pool request topic publishing.
- Keep `Correlation Data`-based reply correlation.
- Require and parse `a2a-responder-agent-id` on pooled responses.
- Persist responder identity with `Task.id` for follow-up routing.
- Keep responder-specific follow-up traffic off pooled topic.

### Failure Cases to Test

- Missing `a2a-responder-agent-id` in pooled reply: requester treats as protocol error.
- Responder unavailable after initial assignment: requester retries with task-aware policy.
- Mixed-capability pool members: requester receives unsupported-operation errors and should apply pool compatibility checks.

