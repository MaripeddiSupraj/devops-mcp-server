"""tools/pagerduty/pagerduty_tools.py — PagerDuty incident management tools."""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from integrations.pagerduty_client import PagerDutyClient

# ── pagerduty_list_incidents ──────────────────────────────────────────────────

LIST_TOOL_NAME = "pagerduty_list_incidents"
LIST_TOOL_DESCRIPTION = (
    "Lists PagerDuty incidents, optionally filtered by status. "
    "Returns title, status, urgency, service name, creation time, and assignees. "
    "Requires PAGERDUTY_API_KEY."
)
LIST_TOOL_INPUT_SCHEMA: Dict[str, Any] = {
    "type": "object",
    "properties": {
        "status": {
            "type": "string",
            "enum": ["triggered", "acknowledged", "resolved"],
            "description": "Filter by incident status (omit for all).",
        },
        "limit": {"type": "integer", "description": "Maximum incidents to return (default: 25).", "default": 25},
    },
    "additionalProperties": False,
}


def list_handler(status: Optional[str] = None, limit: int = 25) -> List[Dict[str, Any]]:
    return PagerDutyClient().list_incidents(status=status, limit=limit)


# ── pagerduty_acknowledge ─────────────────────────────────────────────────────

ACK_TOOL_NAME = "pagerduty_acknowledge_incident"
ACK_TOOL_DESCRIPTION = "Acknowledges a PagerDuty incident by ID, signalling that someone is investigating."
ACK_TOOL_INPUT_SCHEMA: Dict[str, Any] = {
    "type": "object",
    "properties": {
        "incident_id": {"type": "string", "description": "PagerDuty incident ID (e.g. 'P1234AB')."},
    },
    "required": ["incident_id"],
    "additionalProperties": False,
}


def ack_handler(incident_id: str) -> Dict[str, Any]:
    return PagerDutyClient().acknowledge_incident(incident_id)


# ── pagerduty_resolve ─────────────────────────────────────────────────────────

RESOLVE_TOOL_NAME = "pagerduty_resolve_incident"
RESOLVE_TOOL_DESCRIPTION = "Resolves a PagerDuty incident by ID, marking it as fixed."
RESOLVE_TOOL_INPUT_SCHEMA: Dict[str, Any] = {
    "type": "object",
    "properties": {
        "incident_id": {"type": "string", "description": "PagerDuty incident ID."},
    },
    "required": ["incident_id"],
    "additionalProperties": False,
}


def resolve_handler(incident_id: str) -> Dict[str, Any]:
    return PagerDutyClient().resolve_incident(incident_id)


# ── pagerduty_create_incident ─────────────────────────────────────────────────

CREATE_TOOL_NAME = "pagerduty_create_incident"
CREATE_TOOL_DESCRIPTION = (
    "Creates a new PagerDuty incident for a service. "
    "Requires PAGERDUTY_EMAIL (the From header) and either service_id "
    "or the PAGERDUTY_SERVICE_ID environment variable."
)
CREATE_TOOL_INPUT_SCHEMA: Dict[str, Any] = {
    "type": "object",
    "properties": {
        "title": {"type": "string", "description": "Incident title."},
        "service_id": {"type": "string", "description": "PagerDuty service ID to associate (optional if PAGERDUTY_SERVICE_ID is set)."},
        "urgency": {
            "type": "string",
            "enum": ["high", "low"],
            "description": "Incident urgency (default: high).",
            "default": "high",
        },
        "body": {"type": "string", "description": "Detailed description of the incident (optional).", "default": ""},
    },
    "required": ["title"],
    "additionalProperties": False,
}


def create_handler(title: str, service_id: Optional[str] = None, urgency: str = "high", body: str = "") -> Dict[str, Any]:
    return PagerDutyClient().create_incident(title, service_id=service_id, urgency=urgency, body=body)
