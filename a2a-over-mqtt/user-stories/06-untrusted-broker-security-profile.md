# User Story 06: Untrusted-Broker Security Profile

Implementation-oriented user story for SDK development.

## One Request/Stream Exchange with End-to-End Encrypted Payloads

### Goal

Agent A and Agent B exchange request/reply/stream payloads over MQTT where broker ACLs are not assumed to provide sufficient confidentiality.

### Preconditions

- Both agents support `ubsp-v1`.
- Both agents expose discoverable public key metadata (for example trusted `jwksUri` metadata in Agent Card extensions).
- Agent A has trust policy for key source validation and can resolve Agent B encryption key.
- Agent A has an active reply topic subscription.

### End-to-End Flow

1. Agent A discovers Agent B and resolves Agent B encryption key from trusted metadata.
2. Agent A builds a JSON-RPC request payload and encrypts it as JWE.
3. Agent A publishes request to:
   - `$a2a/v1/request/{org_id}/{unit_id}/{agent_id}`
   - QoS: `1` (recommended)
   - MQTT `Content Type`: `application/jose+json` (or `application/jose`)
   - MQTT v5 properties:
     - `Response Topic`: `$a2a/v1/reply/{org_id}/{unit_id}/{client_agent_id}/{reply_suffix}`
     - `Correlation Data`: unique request correlation bytes
     - `a2a-security-profile=ubsp-v1`
     - `a2a-requester-agent-id=<requester_agent_id>`
     - `a2a-recipient-agent-id=<responder_agent_id>`
     - optional `a2a-recipient-kid=<jwk_kid>`
4. Agent B validates request metadata:
   - `a2a-security-profile=ubsp-v1` present
   - `a2a-recipient-agent-id` matches local agent identity
   - decrypts payload and processes request
5. Agent B encrypts reply/stream payloads to Agent A key and publishes to `Response Topic`:
   - echoes `Correlation Data`
   - sets `a2a-security-profile=ubsp-v1`
   - sets `a2a-requester-agent-id=<requester_agent_id>`
   - sets `a2a-responder-agent-id=<responder_agent_id>`
6. Agent A decrypts responses and processes A2A/JSON-RPC semantics as usual.
7. For stream flows, terminal `TaskStatusUpdateEvent.status.state` still closes the stream (`TASK_STATE_COMPLETED`, `TASK_STATE_FAILED`, `TASK_STATE_CANCELED`).

### SDK Requirements Checklist

- Discover and validate responder key metadata using trust policy.
- Encrypt outgoing request payloads and decrypt incoming reply/stream payloads.
- Validate mandatory `ubsp-v1` MQTT User Properties on both request and response paths.
- Preserve and match `Correlation Data` independent of payload encryption.
- Keep OAuth bearer token handling independent from payload encryption rules.
- Enforce replay protection for protected payloads (for example `jti` and short-lived `exp`).

### Failure Cases to Test

- `a2a-recipient-agent-id` mismatch on responder: reject as `transport_protocol_error`.
- Missing `a2a-security-profile` or malformed protected metadata: reject as `transport_protocol_error`.
- Key resolution failure (no trusted responder key): requester must fail closed (do not send plaintext fallback automatically).
- JWE decrypt failure on responder/requester: reject message and surface protocol error.
- Replay-detected protected message: reject as security failure.
