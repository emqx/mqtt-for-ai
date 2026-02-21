# User Story 01: Security OAuth

Implementation-oriented user story for SDK development.

## Discover on MQTT, Authorize with OAuth 2.0, Stream Reply

### Goal

A user asks Agent A to complete a task with Agent B. Agent A discovers Agent B from the MQTT broker, obtains an OAuth 2.0 access token (with user help if needed), sends a request over MQTT, and consumes streamed updates until terminal task state.

### Actors

- User: human operator of Agent A
- Agent A: requester/client
- Agent B: responder/server
- Broker: MQTT v5 broker
- IdP/AS: OAuth 2.0 authorization server

### Preconditions

- Agent B publishes retained Agent Card at:
  - `$a2a/v1/discovery/{org_id}/{unit_id}/{agent_id}`
- Agent B card includes:
  - `supportedInterfaces` with MQTT binding
  - `securitySchemes` + `securityRequirements` requiring OAuth scopes
- Agent A has broker credentials and can connect to MQTT v5.

### End-to-End Flow

1. Agent A subscribes to:
   - `$a2a/v1/discovery/{org_id}/+/+`
2. Agent A receives retained cards and selects Agent B.
3. Agent A checks required security scopes from Agent B card.
4. Agent A obtains OAuth token from IdP/AS:
   - If interactive flow is needed, Agent A asks the user to complete login/MFA.
   - Agent A receives `access_token`.
5. Agent A sends request to Agent B:
   - Topic: `$a2a/v1/request/{org_id}/{unit_id}/{agent_id}`
   - QoS: `1` (recommended)
   - MQTT v5 properties:
     - `Response Topic`: `$a2a/v1/reply/{org_id}/{unit_id}/{agent_id}/{reply_suffix}`
     - `Correlation Data`: request identifier bytes
     - User Property key: `a2a-authorization`
     - User Property value: `Bearer <access_token>`
6. Agent B validates token and scopes, then starts processing.
7. Agent B publishes stream updates as discrete messages to the provided `Response Topic`:
   - Reuses same `Correlation Data`
   - Payloads contain A2A stream items (for example `TaskStatusUpdateEvent`, `TaskArtifactUpdateEvent`)
   - QoS: `1` (recommended)
8. Agent A consumes updates and tracks task progress.
9. Agent A stops stream handling when it receives terminal task status:
   - `TASK_STATE_COMPLETED`
   - `TASK_STATE_FAILED`
   - `TASK_STATE_CANCELED`

### SDK Requirements Checklist

- Discovery:
  - Support retained card discovery subscription.
  - Parse `supportedInterfaces` and choose MQTT-capable interface.
- Security:
  - Support OAuth token acquisition and refresh.
  - Support optional human-in-the-loop auth prompts for interactive flows.
- Request:
  - Set `Response Topic` and `Correlation Data`.
  - Attach bearer token in MQTT v5 User Property per request.
- Reply stream:
  - Route by `Correlation Data`.
  - Decode status/artifact updates.
  - End stream on terminal task state.
- Reliability:
  - Use QoS `1` for request/reply stream by default.
  - Surface PUBACK reason codes for troubleshooting.

### Failure Cases to Test

- Token missing/expired: responder returns auth failure.
- Insufficient scope: responder returns authorization failure.
- No matching subscribers: requester sees PUBACK reason code.
- Stream interrupted: requester can retry request with new correlation ID.
