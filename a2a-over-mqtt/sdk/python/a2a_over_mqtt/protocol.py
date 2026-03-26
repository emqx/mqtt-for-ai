"""A2A-over-MQTT protocol: message types, builders, classification, validation.

Everything here is pure computation with no I/O. The mqtt module handles MQTT v5
transport (connection, properties); high-level classes (Requester, Responder)
handle async I/O on top.
"""

import json
import time
import uuid
from dataclasses import dataclass, field


# --- Proto JSON wire format mapping (A2A v1.0.0 Section 5.5) ---

_STATE_TO_WIRE = {
    "submitted": "TASK_STATE_SUBMITTED",
    "working": "TASK_STATE_WORKING",
    "completed": "TASK_STATE_COMPLETED",
    "failed": "TASK_STATE_FAILED",
    "canceled": "TASK_STATE_CANCELED",
    "input-required": "TASK_STATE_INPUT_REQUIRED",
    "auth-required": "TASK_STATE_AUTH_REQUIRED",
    "rejected": "TASK_STATE_REJECTED",
}

_WIRE_TO_STATE = {v: k for k, v in _STATE_TO_WIRE.items()}

_ROLE_TO_WIRE = {"user": "ROLE_USER", "agent": "ROLE_AGENT"}

# --- A2A error codes (Mandatory Binding-Specific Error Mapping) ---

A2A_REQUEST_EXPIRED = -32003
A2A_RESPONDER_UNAVAILABLE = -32004
A2A_TRANSPORT_PROTOCOL_ERROR = -32005
A2A_PARSE_ERROR = -32700
A2A_INVALID_PARAMS = -32602

_A2A_ERROR_MAP = {
    A2A_REQUEST_EXPIRED: "request_expired",
    A2A_RESPONDER_UNAVAILABLE: "responder_unavailable",
    A2A_TRANSPORT_PROTOCOL_ERROR: "transport_protocol_error",
}


def make_a2a_error(code: int, message: str) -> dict:
    """Build an A2A error dict with data.a2a_error for transport error codes."""
    error: dict = {"code": code, "message": message}
    if code in _A2A_ERROR_MAP:
        error["data"] = {"a2a_error": _A2A_ERROR_MAP[code]}
    return error


# --- A2A response wrapper ---


@dataclass
class A2AResponse:
    """JSON-RPC 2.0 response wrapper for A2A messages."""

    id: str
    result: dict | None = None
    error: dict | None = None

    def to_json(self) -> str:
        d: dict = {"jsonrpc": "2.0", "id": self.id}
        if self.error is not None:
            d["error"] = self.error
        else:
            d["result"] = self.result or {}
        return json.dumps(d)


# --- Status events ---


def make_status_event(
    request_id: str,
    task_id: str,
    state: str,
    message: str = "",
    context_id: str = "",
    *,
    metadata: dict | None = None,
) -> str:
    """Build a TaskStatusUpdateEvent JSON-RPC response.

    Per A2A v1.0.0 proto: StreamResponse wraps TaskStatusUpdateEvent via the
    ``statusUpdate`` oneof field. TaskStatusUpdateEvent carries taskId,
    contextId, status (TaskStatus), and event-level metadata. TaskStatus
    contains state (SCREAMING_SNAKE_CASE enum) and an optional Message object.

    ``state`` accepts short internal names ("submitted", "working", ...);
    they are mapped to proto enum names on the wire.

    ``message`` is wrapped into a proper A2A Message object with ROLE_AGENT.
    ``metadata`` is placed on the event envelope (not inside status).
    """
    wire_state = _STATE_TO_WIRE.get(state, state)
    status: dict = {"state": wire_state}
    if message:
        status["message"] = {
            "messageId": uuid.uuid4().hex,
            "role": _ROLE_TO_WIRE["agent"],
            "parts": [{"text": message}],
        }
    event: dict = {
        "taskId": task_id,
        "contextId": context_id,
        "status": status,
    }
    if metadata:
        event["metadata"] = metadata
    return json.dumps(
        {"jsonrpc": "2.0", "id": request_id, "result": {"statusUpdate": event}}
    )


def make_artifact_event(
    request_id: str,
    task_id: str,
    artifact_text: str,
    context_id: str = "",
    *,
    artifact_id: str = "",
    metadata: dict | None = None,
    last_chunk: bool = True,
) -> str:
    """Build a TaskArtifactUpdateEvent JSON-RPC response.

    Per A2A v1.0.0 proto: StreamResponse wraps TaskArtifactUpdateEvent via the
    ``artifactUpdate`` oneof field. Delivers result content as an Artifact.
    """
    event: dict = {
        "taskId": task_id,
        "contextId": context_id,
        "artifact": {
            "artifactId": artifact_id or uuid.uuid4().hex[:12],
            "parts": [{"text": artifact_text}],
        },
        "lastChunk": last_chunk,
    }
    if metadata:
        event["metadata"] = metadata
    return json.dumps(
        {"jsonrpc": "2.0", "id": request_id, "result": {"artifactUpdate": event}}
    )


# --- Reply classification ---

REPLY_SUBMITTED = "submitted"
REPLY_TEXT = "text"
REPLY_TOOL = "tool_use"
REPLY_ARTIFACT = "artifact"
REPLY_TERMINAL = "terminal"
REPLY_INPUT_REQUIRED = "input_required"
REPLY_FAILED = "failed"
REPLY_ERROR = "error"
REPLY_TIMEOUT = "timeout"

TERMINAL_KINDS = frozenset(
    {
        REPLY_TERMINAL,
        REPLY_INPUT_REQUIRED,
        REPLY_FAILED,
        REPLY_ERROR,
        REPLY_TIMEOUT,
    }
)


def _extract_message_text(status: dict) -> str:
    """Extract text from a TaskStatus.message (Message object or plain string)."""
    msg = status.get("message", "")
    if isinstance(msg, dict):
        parts = msg.get("parts", [])
        return parts[0].get("text", "") if parts else ""
    return msg


def classify_reply(data: dict) -> tuple[str, str]:
    """Classify an A2A reply message. Returns (kind, content).

    kind is one of: REPLY_TEXT, REPLY_TOOL, REPLY_ARTIFACT, REPLY_TERMINAL,
    REPLY_INPUT_REQUIRED, REPLY_FAILED, REPLY_ERROR, or "" for unrecognized.

    Parses proto3 JSON StreamResponse: result contains either ``statusUpdate``
    or ``artifactUpdate`` as the oneof wrapper key.
    """
    if "error" in data:
        err = data["error"]
        return REPLY_ERROR, err.get("message", str(err))

    result = data.get("result", {})

    # Artifact update (StreamResponse.artifact_update)
    artifact_update = result.get("artifactUpdate")
    if artifact_update:
        parts = artifact_update.get("artifact", {}).get("parts", [])
        text = parts[0].get("text", "") if parts else ""
        return REPLY_ARTIFACT, text

    # Status update (StreamResponse.status_update)
    status_update = result.get("statusUpdate")
    if not status_update:
        return "", ""

    status = status_update.get("status", {})
    wire_state = status.get("state", "")
    state = _WIRE_TO_STATE.get(wire_state, wire_state)
    # Event-level metadata; fall back to status.metadata for compat
    meta = status_update.get("metadata") or status.get("metadata") or {}

    if state == "submitted":
        task_id = status_update.get("taskId", "")
        return REPLY_SUBMITTED, task_id

    if state == "working":
        message = _extract_message_text(status)
        msg_type = meta.get("type", "text")
        if msg_type == "tool_use":
            return REPLY_TOOL, message
        return REPLY_TEXT, message

    if state == "completed":
        message = _extract_message_text(status)
        return REPLY_TERMINAL, message

    # Interrupted states: stream-final per spec, but task is not terminal
    if state in ("input-required", "auth-required"):
        message = _extract_message_text(status)
        return REPLY_INPUT_REQUIRED, message or state

    if state in ("failed", "canceled", "rejected"):
        message = _extract_message_text(status)
        return REPLY_FAILED, message or f"Task {state}"

    return "", ""


# --- Core messaging types ---


@dataclass
class A2ARequest:
    """JSON-RPC 2.0 request for A2A message/send."""

    text: str
    request_id: str
    task_id: str | None = None
    context_id: str | None = None
    sender: str = ""
    variables: dict[str, str] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if self.task_id is None:
            self.task_id = str(uuid.uuid4())
        if self.context_id is None:
            self.context_id = str(uuid.uuid4())

    def to_json(self) -> str:
        metadata: dict = {}
        if self.sender:
            metadata["sender"] = self.sender
        if self.variables:
            metadata["variables"] = self.variables
        message: dict = {
            "messageId": uuid.uuid4().hex,
            "role": _ROLE_TO_WIRE["user"],
            "parts": [{"text": self.text}],
            "taskId": self.task_id,
            "contextId": self.context_id,
        }
        params: dict = {"message": message}
        if metadata:
            params["metadata"] = metadata
        return json.dumps(
            {
                "jsonrpc": "2.0",
                "id": self.request_id,
                "method": "message/send",
                "params": params,
            }
        )

    @classmethod
    def from_json(cls, data: str | dict) -> "A2ARequest":
        d = json.loads(data) if isinstance(data, str) else data
        params = d.get("params", {})
        message = params.get("message", {})
        metadata = params.get("metadata", {})
        parts = message.get("parts", [])
        text = parts[0].get("text", "") if parts else ""
        task_id = message.get("taskId", "")
        # Preserve wire value; empty means "untracked" (do not auto-generate,
        # otherwise dedup context_id mismatch rejects retries that omit it).
        context_id = message.get("contextId") or ""
        return cls(
            text=text,
            request_id=d.get("id", f"req-{time.time_ns()}"),
            task_id=task_id,
            context_id=context_id,
            sender=metadata.get("sender", ""),
            variables=metadata.get("variables", {}),
        )


@dataclass
class TaskTarget:
    """A2A agent address for task dispatch."""

    agent: str  # A2A agent address: {org}/{unit}/{agent_id}


# --- Validation ---


@dataclass
class ValidationError:
    """Structured validation failure for an inbound A2A request."""

    code: int
    message: str

    def to_response(self, correlation: str) -> A2AResponse:
        return A2AResponse(
            id=correlation, error=make_a2a_error(self.code, self.message)
        )


def validate_a2a_request(
    payload: dict | str | bytes,
    response_topic: str | None,
    correlation_data: str | None,
) -> A2ARequest | ValidationError:
    """Parse and validate an inbound A2A request. Pure function, no I/O.

    Returns A2ARequest on success or ValidationError on failure.
    Caller is responsible for sending error responses if needed.
    Accepts a pre-parsed dict to avoid redundant JSON parsing.
    """
    if not isinstance(payload, dict):
        if not payload:
            return ValidationError(A2A_TRANSPORT_PROTOCOL_ERROR, "Empty payload")
        if isinstance(payload, (bytes, bytearray)):
            payload = payload.decode("utf-8")

    if not response_topic or not correlation_data:
        return ValidationError(
            A2A_TRANSPORT_PROTOCOL_ERROR,
            "Missing MQTT v5 Response Topic or Correlation Data",
        )

    try:
        req = A2ARequest.from_json(payload)
    except Exception as e:
        return ValidationError(A2A_PARSE_ERROR, f"Parse error: {e}")

    if not req.task_id:
        return ValidationError(
            A2A_TRANSPORT_PROTOCOL_ERROR,
            "Missing required Task.id (message.taskId)",
        )

    return req
