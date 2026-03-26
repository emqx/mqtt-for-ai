"""A2A-over-MQTT Python SDK."""

from a2a_over_mqtt.discovery import build_card, parse_card
from a2a_over_mqtt.mqtt import (
    MqttConfig,
    get_correlation_data,
    get_response_topic,
    make_properties,
)
from a2a_over_mqtt.protocol import (
    A2A_INVALID_PARAMS,
    A2A_PARSE_ERROR,
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
    REPLY_TIMEOUT,
    REPLY_TOOL,
    TERMINAL_KINDS,
    TaskTarget,
    ValidationError,
    classify_reply,
    make_a2a_error,
    make_artifact_event,
    make_status_event,
    validate_a2a_request,
)
from a2a_over_mqtt.requester import Requester
from a2a_over_mqtt.responder import Responder
from a2a_over_mqtt.topics import TopicSpace

__all__ = [
    # mqtt
    "MqttConfig",
    "make_properties",
    "get_correlation_data",
    "get_response_topic",
    # topics
    "TopicSpace",
    # protocol
    "A2ARequest",
    "A2AResponse",
    "TaskTarget",
    "ValidationError",
    "classify_reply",
    "make_status_event",
    "make_artifact_event",
    "make_a2a_error",
    "validate_a2a_request",
    "REPLY_SUBMITTED",
    "REPLY_TEXT",
    "REPLY_TOOL",
    "REPLY_ARTIFACT",
    "REPLY_TERMINAL",
    "REPLY_INPUT_REQUIRED",
    "REPLY_FAILED",
    "REPLY_ERROR",
    "REPLY_TIMEOUT",
    "TERMINAL_KINDS",
    "A2A_REQUEST_EXPIRED",
    "A2A_RESPONDER_UNAVAILABLE",
    "A2A_TRANSPORT_PROTOCOL_ERROR",
    "A2A_INVALID_PARAMS",
    "A2A_PARSE_ERROR",
    # discovery
    "build_card",
    "parse_card",
    # high-level
    "Requester",
    "Responder",
]
