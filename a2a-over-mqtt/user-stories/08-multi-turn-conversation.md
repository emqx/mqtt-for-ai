# User Story 08: Multi-Turn Conversation

Implementation-oriented user story for SDK development.

## Send Follow-Up Turns Using `Task.context_id` and Resume Interrupted Tasks

### Goal

Agent A holds a multi-turn conversation with Agent B: multiple request/reply exchanges are grouped by a shared `Task.context_id` so Agent B can maintain conversational continuity. When Agent B needs additional input mid-task, Agent A resumes the same task after prompting the user.

### Preconditions

- Agent B is registered and discovered by Agent A.
- Agent A has subscribed to its reply topic.
- Agent B supports multi-turn conversations (maintains context across tasks sharing a `Task.context_id`).

### End-to-End Flow — Follow-Up Turns

#### Turn 1: Start Conversation

1. Agent A generates `Task.context_id` **C** (UUIDv4) and `Task.id` **T1** (UUIDv4).
2. Agent A publishes `message/send` to:
   - `$a2a/v1/request/{org_id}/{unit_id}/{agent_b_id}`
   - QoS: `1` (recommended)
   - MQTT v5 properties:
     - `Response Topic`: `$a2a/v1/reply/{org_id}/{unit_id}/{agent_a_id}/{reply_suffix}`
     - `Correlation Data`: **D1** (unique request correlation bytes)
   - Optional MQTT User Property: `a2a-context-id` = **C**
   - JSON-RPC payload includes `Message.task_id = T1` and `Message.context_id = C`
3. Agent B creates task **T1** within context **C**, processes the request.
4. Agent B streams `TaskStatusUpdateEvent` / `TaskArtifactUpdateEvent` messages echoing **D1**.
5. Agent B sends terminal status (`completed`) echoing **D1**. Agent A marks **T1** complete.

#### Turn 2: Follow-Up in Same Conversation

6. User asks a follow-up question.
7. Agent A generates new `Task.id` **T2** (UUIDv4), reuses `Task.context_id` **C**.
8. Agent A publishes `message/send`:
   - `Correlation Data`: **D2** (fresh)
   - JSON-RPC payload includes `Message.task_id = T2` and `Message.context_id = C`
9. Agent B creates task **T2** within context **C**. Agent B uses prior context from **T1** to inform its response.
10. Agent B streams replies echoing **D2**, completes with terminal status.

### End-to-End Flow — Interrupted Task (`input-required`)

#### Initial Request

1. Agent A publishes `message/send` with `Task.id` **T3**, `Task.context_id` **C**, `Correlation Data` **D3**.
2. Agent B starts processing, streams partial results echoing **D3**.

#### Input Required

3. Agent B determines it needs more information from the user.
4. Agent B publishes `TaskStatusUpdateEvent` with `status.state = input-required` and a message describing what input is needed, echoing **D3**.
5. Agent A receives `input-required`, treats it as stream-final for **D3**, cleans up in-flight state, and prompts the user.

#### User Provides Input

6. User provides the requested information.
7. Agent A publishes a new `message/send` with the **same** `Task.id` **T3** and `Task.context_id` **C**, fresh `Correlation Data` **D4**.
8. Agent B continues processing task **T3** with the new input, streams replies echoing **D4**.
9. Agent B sends terminal status (`completed`) echoing **D4**.

### SDK Requirements Checklist

- Generate and persist `Task.context_id` (UUIDv4) for new conversations; reuse for follow-up turns.
- Include `Message.context_id` in JSON-RPC payload on all requests within a conversation.
- Optionally include MQTT User Property `a2a-context-id` for transport-level visibility.
- Detect `input-required` / `auth-required` status as stream-final for current correlation.
- Resume interrupted tasks: publish new `message/send` with same `Task.id` and `Task.context_id`, fresh `Correlation Data`.
- Responder SDK: provide access to prior task results within the same `Task.context_id` for context-aware responses.
- Responder SDK: validate `Task.context_id` consistency — reject if provided `Task.context_id` conflicts with existing task's `Task.context_id`.

### Failure Cases to Test

- Mismatched `Task.context_id`: Agent A sends a follow-up for an existing `Task.id` with a different `Task.context_id`. Agent B rejects with JSON-RPC error `-32602` (invalid params).
- Unknown `Task.context_id`: Agent A sends a new `Task.id` with a `Task.context_id` the responder hasn't seen. Agent B creates a new context (no error — the context is new).
- Expired context: Agent A sends a follow-up after Agent B's context expiration window. Agent B returns an appropriate error.
- Multiple concurrent tasks in same context: Agent A has two in-flight tasks (**T4**, **T5**) sharing the same `Task.context_id` **C**. Both complete independently; each uses its own `Correlation Data`.
