# User Story 02: One Request, One Response

Implementation-oriented user story for SDK development.

## Send a Task Request and Receive a Single Reply

### Goal

Agent A sends one request to Agent B and receives exactly one response message on the reply topic.

### Preconditions

- Agent B is discoverable on:
  - `$a2a/v1/discovery/{org_id}/{unit_id}/{agent_id}`
- Agent A has selected Agent B and has a writable request topic plus a subscribed reply topic.

### End-to-End Flow

1. Agent A subscribes to reply topic:
   - `$a2a/v1/reply/{org_id}/{unit_id}/{agent_id}/{reply_suffix}`
2. Agent A publishes one request to:
   - `$a2a/v1/request/{org_id}/{unit_id}/{agent_id}`
   - QoS: `1` (recommended)
   - MQTT v5 properties:
     - `Response Topic`: reply topic above
     - `Correlation Data`: unique request correlation bytes
3. Agent B processes request and publishes one response message to `Response Topic`:
   - Echoes the same `Correlation Data`
4. Agent A matches response by `Correlation Data` and completes the request.

### Expected Payload Outcome

- Response payload may contain:
  - `message`
  - `task`
- If `task` is present, `task.id` is server-generated and becomes the identifier for any follow-up task operations.

### SDK Requirements Checklist

- Generate unique `Correlation Data` per request.
- Route response strictly by `Correlation Data`.
- Handle one-shot completion without waiting for stream updates.
- Persist returned `task.id` when present.

