# Use Cases

A2A over MQTT is suitable for distributed agent systems that need broker-neutral discovery and reliable request/reply messaging.
This page is aligned with the user stories in `user-stories/`:

- **Security OAuth** (`01-security-oauth.md`): discover via MQTT, acquire OAuth token, and send authenticated requests using MQTT User Property `a2a-authorization`.
- **One request, one response** (`02-request-single-response.md`): synchronous request/reply with `Response Topic` and `Correlation Data`.
- **One request, multiple responses** (`03-request-multi-response.md`): stream task status and artifact updates on reply topic until terminal task state.
- **One request, multiple binary artifact responses** (`04-request-multi-binary-artifact-responses.md`): request `a2a-artifact-mode=binary` and receive chunked binary artifact updates.
- **Shared pool dispatch** (`05-shared-pool-dispatch.md`): publish to unit-level pool topic and route follow-up operations using `a2a-responder-agent-id` and server-generated `Task.id`.
