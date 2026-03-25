# Use Cases

A2A over MQTT is suitable for distributed agent systems that need broker-neutral discovery and reliable request/reply messaging.
This page is aligned with the user stories in `user-stories/`:

- **Security OAuth** (`01-security-oauth.md`): discover via MQTT, acquire OAuth token, and send authenticated requests using MQTT User Property `a2a-authorization`.
- **One request, one response** (`02-request-single-response.md`): synchronous request/reply with `Response Topic` and `Correlation Data`.
- **One request, multiple responses** (`03-request-multi-response.md`): stream task status and artifact updates on reply topic until terminal task state.
- **One request, multiple binary artifact responses** (`04-request-multi-binary-artifact-responses.md`): request `a2a-artifact-mode=binary` and receive chunked binary artifact updates.
- **Shared pool dispatch** (`05-shared-pool-dispatch.md`): publish to unit-level pool topic and route follow-up operations using `a2a-responder-agent-id` and requester-generated `Task.id`.
- **Untrusted-broker security profile** (`06-untrusted-broker-security-profile.md`): use `a2a-security-profile=ubsp-v1` for end-to-end encrypted request/reply/stream payloads with key discovery and property validation.
- **Task handover** (`07-task-handover.md`): card-owning agent delegates an in-progress task to a spawned instance; requester routes follow-up operations using `a2a-responder-agent-id`.
- **Multi-turn conversation** (`08-multi-turn-conversation.md`): group multiple request/reply exchanges into a conversation using `Task.context_id` and resume interrupted tasks via `input-required` continuation.
- **Presence lifecycle** (`09-presence-lifecycle.md`): agent liveness signaled via `a2a-status` User Property on retained Agent Card publications, with LWT for crash detection and graceful offline for planned shutdowns.
