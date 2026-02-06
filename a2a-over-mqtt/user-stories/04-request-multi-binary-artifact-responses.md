# User Story 04: One Request, Multiple Binary Artifact Responses

Implementation-oriented user story for SDK development.

## Request Binary Artifact Mode and Receive Chunked Binary Replies

### Goal

Agent A requests native binary artifact mode and receives multiple binary artifact chunks from Agent B over the reply stream.

### Preconditions

- Both peers support optional MQTT native binary artifact mode.
- Agent A can decode binary chunks and reassemble artifacts by sequence.

### End-to-End Flow

1. Agent A publishes one request to:
   - `a2a/v1/request/{org_id}/{unit_id}/{agent_id}`
   - QoS: `1` (recommended)
   - MQTT v5 properties:
     - `Response Topic`: `a2a/v1/reply/{org_id}/{unit_id}/{agent_id}/{reply_suffix}`
     - `Correlation Data`: unique request correlation bytes
     - User Property key: `a2a-artifact-mode`
     - User Property value: `binary`
2. Agent B selects mode:
   - If supported, reply uses `a2a-artifact-mode=binary`.
   - If unsupported, fallback is `a2a-artifact-mode=json`.
3. In binary mode, Agent B publishes artifact chunk messages to reply topic:
   - Echoes same `Correlation Data`
   - MQTT Payload Format Indicator: `0`
   - MQTT Content Type set when media type is known
   - User Properties include:
     - `a2a-event-type=task-artifact-update`
     - `a2a-task-id=<task_id>`
     - `a2a-artifact-id=<artifact_id>`
     - `a2a-chunk-seqno=<0..N>`
     - `a2a-last-chunk=true|false`
   - Optional:
     - `a2a-context-id=<context_id>`
4. Agent A reassembles artifact chunks by `a2a-artifact-id` + `a2a-chunk-seqno`.
5. `a2a-last-chunk=true` marks artifact chunk completion (artifact done, not necessarily task done).
6. Stream ends only when terminal task status arrives:
   - `TASK_STATE_COMPLETED`
   - `TASK_STATE_FAILED`
   - `TASK_STATE_CANCELED`

### SDK Requirements Checklist

- Support request-side mode selection via `a2a-artifact-mode`.
- Support responder mode confirmation from reply properties.
- Validate required binary chunk metadata fields.
- Reassemble by strict sequence (`a2a-chunk-seqno`).
- Keep task lifecycle separate from artifact chunk lifecycle.
- Fallback cleanly to JSON mode when binary mode is unavailable.

