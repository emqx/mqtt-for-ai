"""Tests for A2A protocol layer (pure, no I/O)."""

import json

from a2a_over_mqtt.protocol import (
    A2A_REQUEST_EXPIRED,
    A2A_RESPONDER_UNAVAILABLE,
    A2A_TRANSPORT_PROTOCOL_ERROR,
    A2ARequest,
    A2AResponse,
    REPLY_ARTIFACT,
    REPLY_ERROR,
    REPLY_FAILED,
    REPLY_INPUT_REQUIRED,
    REPLY_SUBMITTED,
    REPLY_TERMINAL,
    REPLY_TEXT,
    REPLY_TOOL,
    TaskState,
    ValidationError,
    _extract_part_text,
    _extract_parts_text,
    classify_reply,
    make_a2a_error,
    make_artifact_event,
    make_status_event,
    validate_a2a_request,
)


# --- A2ARequest ---


class TestA2ARequest:
    def test_roundtrip(self):
        req = A2ARequest(
            text="Research quantum computing",
            request_id="req-abc123",
            task_id="550e8400-e29b-41d4-a716-446655440000",
            sender="cli",
            variables={"topic": "quantum"},
        )
        j = req.to_json()
        d = json.loads(j)
        assert d["jsonrpc"] == "2.0"
        assert d["id"] == "req-abc123"
        assert d["method"] == "SendMessage"
        msg = d["params"]["message"]
        assert msg["parts"][0]["text"] == "Research quantum computing"
        assert msg["taskId"] == "550e8400-e29b-41d4-a716-446655440000"
        assert "messageId" in msg
        assert d["params"]["metadata"]["sender"] == "cli"
        assert d["params"]["metadata"]["variables"]["topic"] == "quantum"

        restored = A2ARequest.from_json(j)
        assert restored.text == "Research quantum computing"
        assert restored.request_id == "req-abc123"
        assert restored.task_id == "550e8400-e29b-41d4-a716-446655440000"
        assert restored.sender == "cli"
        assert restored.variables == {"topic": "quantum"}

    def test_minimal(self):
        import uuid as uuid_mod

        req = A2ARequest(text="hello", request_id="s1")
        assert req.task_id
        uuid_mod.UUID(req.task_id)
        j = req.to_json()
        d = json.loads(j)
        assert "metadata" not in d["params"]
        assert d["params"]["message"]["taskId"] == req.task_id

        restored = A2ARequest.from_json(j)
        assert restored.text == "hello"
        assert restored.task_id == req.task_id
        assert restored.sender == ""
        assert restored.variables == {}

    def test_context_id_in_roundtrip(self):
        ctx = "ctx-11111111-2222-3333-4444-555555555555"
        req = A2ARequest(text="hello", request_id="r1", context_id=ctx, sender="cli")
        j = req.to_json()
        d = json.loads(j)
        assert d["params"]["message"]["contextId"] == ctx

        restored = A2ARequest.from_json(j)
        assert restored.context_id == ctx

    def test_context_id_auto_generated(self):
        import uuid as uuid_mod

        req = A2ARequest(text="hello", request_id="r1")
        assert req.context_id
        uuid_mod.UUID(req.context_id)

    def test_context_id_preserved_from_json(self):
        payload = json.dumps(
            {
                "jsonrpc": "2.0",
                "id": "r1",
                "method": "SendMessage",
                "params": {
                    "message": {
                        "role": "ROLE_USER",
                        "parts": [{"text": "hi"}],
                        "taskId": "t1",
                        "contextId": "ctx-explicit",
                    }
                },
            }
        )
        req = A2ARequest.from_json(payload)
        assert req.context_id == "ctx-explicit"


# --- A2AResponse ---


class TestA2AResponse:
    def test_result_response(self):
        resp = A2AResponse(id="r1", result={"status": "ok"})
        d = json.loads(resp.to_json())
        assert d["jsonrpc"] == "2.0"
        assert d["id"] == "r1"
        assert d["result"] == {"status": "ok"}
        assert "error" not in d

    def test_error_response(self):
        resp = A2AResponse(id="r1", error={"code": -1, "message": "fail"})
        d = json.loads(resp.to_json())
        assert d["error"]["code"] == -1
        assert "result" not in d

    def test_empty_result_default(self):
        resp = A2AResponse(id="r1")
        d = json.loads(resp.to_json())
        assert d["result"] == {}


# --- Status and artifact events ---


class TestStatusEvent:
    def test_working_text(self):
        event = make_status_event(
            "req-1",
            "sess-abc123",
            "working",
            message="hello",
            metadata={"task_name": "research"},
        )
        d = json.loads(event)
        assert d["jsonrpc"] == "2.0"
        assert d["id"] == "req-1"
        su = d["result"]["statusUpdate"]
        assert su["taskId"] == "sess-abc123"
        assert su["status"]["state"] == "TASK_STATE_WORKING"
        msg = su["status"]["message"]
        assert msg["role"] == "ROLE_AGENT"
        assert msg["parts"] == [{"text": "hello"}]
        assert "messageId" in msg
        assert su["metadata"]["task_name"] == "research"

        kind, content = classify_reply(d)
        assert kind == REPLY_TEXT
        assert content == "hello"

    def test_working_tool_use(self):
        event = make_status_event(
            "req-1",
            "sess-abc123",
            "working",
            message="Read: file.py",
            metadata={"type": "tool_use", "task_name": "research"},
        )
        d = json.loads(event)
        su = d["result"]["statusUpdate"]
        assert su["metadata"]["type"] == "tool_use"

        kind, content = classify_reply(d)
        assert kind == REPLY_TOOL
        assert content == "Read: file.py"

    def test_terminal_with_artifact(self):
        artifact_event = make_artifact_event(
            "req-2",
            "sess-def456",
            "Final answer",
            metadata={"task_name": "summarize"},
        )
        status_event = make_status_event("req-2", "sess-def456", "completed")
        da = json.loads(artifact_event)
        ds = json.loads(status_event)
        assert ds["result"]["statusUpdate"]["status"]["state"] == "TASK_STATE_COMPLETED"
        au = da["result"]["artifactUpdate"]
        assert au["artifact"]["parts"][0]["text"] == "Final answer"

        kind_a, content_a = classify_reply(da)
        assert kind_a == REPLY_ARTIFACT
        assert content_a == "Final answer"

        kind_s, content_s = classify_reply(ds)
        assert kind_s == REPLY_TERMINAL
        assert content_s == ""

    def test_error_reply(self):
        kind, content = classify_reply(
            {"error": {"code": -32004, "message": "Unknown agent"}}
        )
        assert kind == REPLY_ERROR
        assert content == "Unknown agent"

    def test_failed_reply(self):
        event = make_status_event(
            "req-3", "sess-xyz", "failed", message="Agent crashed"
        )
        d = json.loads(event)
        kind, content = classify_reply(d)
        assert kind == REPLY_FAILED
        assert content == "Agent crashed"

    def test_failed_reply_no_message_uses_default(self):
        d = {
            "jsonrpc": "2.0",
            "id": "req-4",
            "result": {
                "statusUpdate": {
                    "taskId": "sess-xyz",
                    "status": {"state": "TASK_STATE_FAILED"},
                },
            },
        }
        kind, content = classify_reply(d)
        assert kind == REPLY_FAILED
        assert content == "Task failed"

    def test_canceled_reply(self):
        event = make_status_event(
            "req-5", "sess-xyz", "canceled", message="User canceled"
        )
        d = json.loads(event)
        kind, content = classify_reply(d)
        assert kind == REPLY_FAILED
        assert content == "User canceled"

    def test_rejected_reply(self):
        event = make_status_event(
            "req-6", "sess-xyz", "rejected", message="Request rejected"
        )
        d = json.loads(event)
        kind, content = classify_reply(d)
        assert kind == REPLY_FAILED
        assert content == "Request rejected"

    def test_unknown_message(self):
        kind, content = classify_reply({"something": "else"})
        assert kind == ""
        assert content == ""

    def test_status_event_with_context_id(self):
        event = make_status_event(
            "req-1", "sess-1", "working", message="hi", context_id="ctx-123"
        )
        d = json.loads(event)
        assert d["result"]["statusUpdate"]["contextId"] == "ctx-123"

    def test_context_id_always_present(self):
        event = make_status_event("req-1", "sess-1", "working", message="hi")
        d = json.loads(event)
        assert d["result"]["statusUpdate"]["contextId"] == ""

    def test_artifact_event_has_context_id(self):
        event = make_artifact_event("req-1", "t1", "result", context_id="ctx-1")
        d = json.loads(event)
        assert d["result"]["artifactUpdate"]["contextId"] == "ctx-1"
        event2 = make_artifact_event("req-1", "t1", "result")
        d2 = json.loads(event2)
        assert d2["result"]["artifactUpdate"]["contextId"] == ""

    def test_input_required_is_stream_final(self):
        d = {
            "jsonrpc": "2.0",
            "id": "req-1",
            "result": {
                "statusUpdate": {
                    "taskId": "t1",
                    "contextId": "ctx-1",
                    "status": {
                        "state": "TASK_STATE_INPUT_REQUIRED",
                        "message": {
                            "role": "ROLE_AGENT",
                            "parts": [{"text": "What is your name?"}],
                        },
                    },
                },
            },
        }
        kind, content = classify_reply(d)
        assert kind == REPLY_INPUT_REQUIRED
        assert content == "What is your name?"

    def test_auth_required_is_stream_final(self):
        d = {
            "jsonrpc": "2.0",
            "id": "req-1",
            "result": {
                "statusUpdate": {
                    "taskId": "t1",
                    "contextId": "",
                    "status": {"state": "TASK_STATE_AUTH_REQUIRED"},
                },
            },
        }
        kind, content = classify_reply(d)
        assert kind == REPLY_INPUT_REQUIRED
        assert content == "auth-required"


# --- Error codes ---


class TestErrorCodes:
    def test_error_codes_defined(self):
        assert A2A_REQUEST_EXPIRED == -32003
        assert A2A_RESPONDER_UNAVAILABLE == -32004
        assert A2A_TRANSPORT_PROTOCOL_ERROR == -32005

    def test_make_a2a_error_with_transport_code(self):
        err = make_a2a_error(-32004, "Agent offline")
        assert err["code"] == -32004
        assert err["message"] == "Agent offline"
        assert err["data"]["a2a_error"] == "responder_unavailable"

    def test_make_a2a_error_with_request_expired(self):
        err = make_a2a_error(-32003, "Timed out")
        assert err["data"]["a2a_error"] == "request_expired"

    def test_make_a2a_error_without_transport_code(self):
        err = make_a2a_error(-32602, "Invalid params")
        assert err["code"] == -32602
        assert "data" not in err


# --- validate_a2a_request (pure) ---


class TestValidateA2ARequest:
    def _valid_payload(self, task_id: str = "tid-1") -> str:
        return json.dumps(
            {
                "jsonrpc": "2.0",
                "id": "rpc-1",
                "method": "SendMessage",
                "params": {
                    "message": {
                        "role": "ROLE_USER",
                        "parts": [{"text": "hello"}],
                        "taskId": task_id,
                    }
                },
            }
        )

    def test_valid_request(self):
        result = validate_a2a_request(self._valid_payload(), "reply/t", "corr-1")
        assert isinstance(result, A2ARequest)
        assert result.text == "hello"
        assert result.task_id == "tid-1"

    def test_empty_payload(self):
        result = validate_a2a_request("", "reply/t", "corr-1")
        assert isinstance(result, ValidationError)

    def test_bytes_payload(self):
        result = validate_a2a_request(
            self._valid_payload().encode(), "reply/t", "corr-1"
        )
        assert isinstance(result, A2ARequest)

    def test_missing_response_topic(self):
        result = validate_a2a_request(self._valid_payload(), "", "corr-1")
        assert isinstance(result, ValidationError)
        assert result.code == A2A_TRANSPORT_PROTOCOL_ERROR
        assert "Response Topic" in result.message

    def test_missing_correlation(self):
        result = validate_a2a_request(self._valid_payload(), "reply/t", "")
        assert isinstance(result, ValidationError)
        assert result.code == A2A_TRANSPORT_PROTOCOL_ERROR

    def test_missing_both_props(self):
        result = validate_a2a_request(self._valid_payload(), "", "")
        assert isinstance(result, ValidationError)

    def test_bad_json(self):
        result = validate_a2a_request("not json{{{", "reply/t", "corr-1")
        assert isinstance(result, ValidationError)
        assert result.code == -32700
        assert "Parse error" in result.message

    def test_missing_task_id(self):
        result = validate_a2a_request(
            self._valid_payload(task_id=""), "reply/t", "corr-1"
        )
        assert isinstance(result, ValidationError)
        assert result.code == A2A_TRANSPORT_PROTOCOL_ERROR
        assert "Task.id" in result.message

    def test_validation_error_to_response(self):
        err = ValidationError(code=-32005, message="Bad request")
        resp = err.to_response("corr-99")
        d = json.loads(resp.to_json())
        assert d["id"] == "corr-99"
        assert d["error"]["code"] == -32005
        assert d["error"]["message"] == "Bad request"


# --- TaskState enum ---


class TestTaskState:
    def test_enum_values(self):
        assert TaskState.SUBMITTED == "submitted"
        assert TaskState.WORKING == "working"
        assert TaskState.COMPLETED == "completed"
        assert TaskState.FAILED == "failed"
        assert TaskState.CANCELED == "canceled"
        assert TaskState.INPUT_REQUIRED == "input-required"
        assert TaskState.AUTH_REQUIRED == "auth-required"
        assert TaskState.REJECTED == "rejected"

    def test_string_equality(self):
        """StrEnum members compare equal to plain strings."""
        assert TaskState.WORKING == "working"
        assert "working" == TaskState.WORKING

    def test_unknown_state_raises(self):
        """Strict wire mapping rejects unknown states."""
        import pytest

        with pytest.raises(KeyError):
            make_status_event("r1", "t1", "bogus")


# --- Status timestamp ---


class TestStatusTimestamp:
    def test_status_has_iso_timestamp(self):
        event = make_status_event("req-1", "t1", "working", message="hi")
        d = json.loads(event)
        ts = d["result"]["statusUpdate"]["status"]["timestamp"]
        assert ts  # non-empty
        # Verify ISO 8601 format (contains 'T' and timezone info)
        assert "T" in ts

    def test_timestamp_present_in_all_states(self):
        for state in ("submitted", "working", "completed", "failed", "canceled"):
            event = make_status_event("r1", "t1", state)
            d = json.loads(event)
            assert "timestamp" in d["result"]["statusUpdate"]["status"]


# --- Multi-part extraction ---


class TestPartExtraction:
    def test_text_part(self):
        assert _extract_part_text({"text": "hello"}) == "hello"

    def test_data_part(self):
        result = _extract_part_text({"data": {"key": "value"}})
        assert json.loads(result) == {"key": "value"}

    def test_url_part(self):
        assert _extract_part_text({"url": "https://example.com"}) == "https://example.com"

    def test_raw_part_with_filename(self):
        result = _extract_part_text({"raw": "...", "filename": "doc.pdf"})
        assert result == "[binary: doc.pdf]"

    def test_raw_part_with_media_type(self):
        result = _extract_part_text({"raw": "...", "mediaType": "image/png"})
        assert result == "[binary: image/png]"

    def test_raw_part_default(self):
        result = _extract_part_text({"raw": "..."})
        assert result == "[binary: binary]"

    def test_empty_part(self):
        assert _extract_part_text({}) == ""

    def test_multi_part_concatenation(self):
        parts = [{"text": "hello "}, {"text": "world"}]
        assert _extract_parts_text(parts) == "hello world"

    def test_mixed_parts(self):
        parts = [{"text": "See: "}, {"url": "https://example.com"}]
        assert _extract_parts_text(parts) == "See: https://example.com"


# --- classify_reply: task and message oneofs ---


class TestClassifyReplyTaskOneof:
    def test_task_completed_with_artifacts(self):
        data = {
            "jsonrpc": "2.0",
            "id": "r1",
            "result": {
                "task": {
                    "id": "t1",
                    "status": {"state": "TASK_STATE_COMPLETED"},
                    "artifacts": [
                        {"parts": [{"text": "result text"}]},
                    ],
                }
            },
        }
        kind, content = classify_reply(data)
        assert kind == REPLY_TERMINAL
        assert content == "result text"

    def test_task_completed_prefers_artifact_over_message(self):
        data = {
            "jsonrpc": "2.0",
            "id": "r1",
            "result": {
                "task": {
                    "id": "t1",
                    "status": {
                        "state": "TASK_STATE_COMPLETED",
                        "message": {
                            "parts": [{"text": "status message"}],
                        },
                    },
                    "artifacts": [
                        {"parts": [{"text": "artifact text"}]},
                    ],
                }
            },
        }
        kind, content = classify_reply(data)
        assert kind == REPLY_TERMINAL
        assert content == "artifact text"

    def test_task_failed(self):
        data = {
            "jsonrpc": "2.0",
            "id": "r1",
            "result": {
                "task": {
                    "id": "t1",
                    "status": {
                        "state": "TASK_STATE_FAILED",
                        "message": {"parts": [{"text": "oops"}]},
                    },
                }
            },
        }
        kind, content = classify_reply(data)
        assert kind == REPLY_FAILED
        assert content == "oops"

    def test_task_submitted(self):
        data = {
            "jsonrpc": "2.0",
            "id": "r1",
            "result": {
                "task": {
                    "id": "t1",
                    "status": {"state": "TASK_STATE_SUBMITTED"},
                }
            },
        }
        kind, content = classify_reply(data)
        assert kind == REPLY_SUBMITTED
        assert content == "t1"

    def test_task_input_required(self):
        data = {
            "jsonrpc": "2.0",
            "id": "r1",
            "result": {
                "task": {
                    "id": "t1",
                    "status": {
                        "state": "TASK_STATE_INPUT_REQUIRED",
                        "message": {"parts": [{"text": "Need input"}]},
                    },
                }
            },
        }
        kind, content = classify_reply(data)
        assert kind == REPLY_INPUT_REQUIRED
        assert content == "Need input"


class TestClassifyReplyMessageOneof:
    def test_standalone_message(self):
        data = {
            "jsonrpc": "2.0",
            "id": "r1",
            "result": {
                "message": {
                    "messageId": "m1",
                    "role": "ROLE_AGENT",
                    "parts": [{"text": "hello from agent"}],
                }
            },
        }
        kind, content = classify_reply(data)
        assert kind == REPLY_TEXT
        assert content == "hello from agent"

    def test_message_with_multi_parts(self):
        data = {
            "jsonrpc": "2.0",
            "id": "r1",
            "result": {
                "message": {
                    "parts": [
                        {"text": "part1 "},
                        {"data": {"key": "val"}},
                    ],
                }
            },
        }
        kind, content = classify_reply(data)
        assert kind == REPLY_TEXT
        assert "part1 " in content
        assert '"key"' in content


# --- Artifact append ---


class TestArtifactAppend:
    def test_append_false_by_default(self):
        event = make_artifact_event("r1", "t1", "text")
        d = json.loads(event)
        assert "append" not in d["result"]["artifactUpdate"]

    def test_append_true(self):
        event = make_artifact_event("r1", "t1", "text", append=True)
        d = json.loads(event)
        assert d["result"]["artifactUpdate"]["append"] is True
