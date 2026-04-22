"""tools/datadog/datadog_tools.py — Datadog monitoring and observability tools."""

from __future__ import annotations

import time
from typing import Any, Dict, List, Optional

from integrations.datadog_client import DatadogClient

# ── datadog_list_monitors ─────────────────────────────────────────────────────

LIST_MONITORS_TOOL_NAME = "datadog_list_monitors"
LIST_MONITORS_TOOL_DESCRIPTION = (
    "Lists Datadog monitors with their current status. "
    "Optionally filter by status (Alert, Warn, No Data, OK). "
    "Requires DATADOG_API_KEY and DATADOG_APP_KEY."
)
LIST_MONITORS_TOOL_INPUT_SCHEMA: Dict[str, Any] = {
    "type": "object",
    "properties": {
        "status": {
            "type": "string",
            "enum": ["Alert", "Warn", "No Data", "OK", "Ignored", "Skipped"],
            "description": "Filter by monitor status (omit for all).",
        },
    },
    "additionalProperties": False,
}


def list_monitors_handler(status: Optional[str] = None) -> List[Dict]:
    return DatadogClient().list_monitors(status=status)


# ── datadog_mute_monitor ──────────────────────────────────────────────────────

MUTE_MONITOR_TOOL_NAME = "datadog_mute_monitor"
MUTE_MONITOR_TOOL_DESCRIPTION = (
    "Mutes a Datadog monitor by ID to suppress alerts. "
    "Optionally specify an end timestamp (ISO 8601) when the mute should expire."
)
MUTE_MONITOR_TOOL_INPUT_SCHEMA: Dict[str, Any] = {
    "type": "object",
    "properties": {
        "monitor_id": {"type": "integer", "description": "Datadog monitor ID."},
        "end": {"type": "string", "description": "ISO 8601 datetime when mute expires (optional)."},
    },
    "required": ["monitor_id"],
    "additionalProperties": False,
}


def mute_monitor_handler(monitor_id: int, end: Optional[str] = None) -> Dict:
    return DatadogClient().mute_monitor(monitor_id, end=end)


# ── datadog_unmute_monitor ────────────────────────────────────────────────────

UNMUTE_MONITOR_TOOL_NAME = "datadog_unmute_monitor"
UNMUTE_MONITOR_TOOL_DESCRIPTION = "Unmutes a previously muted Datadog monitor by ID."
UNMUTE_MONITOR_TOOL_INPUT_SCHEMA: Dict[str, Any] = {
    "type": "object",
    "properties": {
        "monitor_id": {"type": "integer", "description": "Datadog monitor ID."},
    },
    "required": ["monitor_id"],
    "additionalProperties": False,
}


def unmute_monitor_handler(monitor_id: int) -> Dict:
    return DatadogClient().unmute_monitor(monitor_id)


# ── datadog_query_metrics ─────────────────────────────────────────────────────

QUERY_METRICS_TOOL_NAME = "datadog_query_metrics"
QUERY_METRICS_TOOL_DESCRIPTION = (
    "Query Datadog metrics using a metric query string (e.g. 'avg:system.cpu.user{*}'). "
    "Returns time-series data for the specified window (minutes back from now)."
)
QUERY_METRICS_TOOL_INPUT_SCHEMA: Dict[str, Any] = {
    "type": "object",
    "properties": {
        "query": {"type": "string", "description": "Datadog metrics query string."},
        "minutes": {"type": "integer", "description": "How many minutes back to query (default: 60).", "default": 60},
    },
    "required": ["query"],
    "additionalProperties": False,
}


def query_metrics_handler(query: str, minutes: int = 60) -> Dict:
    now = int(time.time())
    return DatadogClient().query_metrics(query, from_ts=now - minutes * 60, to_ts=now)


# ── datadog_list_events ───────────────────────────────────────────────────────

LIST_EVENTS_TOOL_NAME = "datadog_list_events"
LIST_EVENTS_TOOL_DESCRIPTION = (
    "List Datadog events from the event stream within the last N minutes. "
    "Optionally filter by priority (normal or low)."
)
LIST_EVENTS_TOOL_INPUT_SCHEMA: Dict[str, Any] = {
    "type": "object",
    "properties": {
        "minutes": {"type": "integer", "description": "How many minutes back to fetch events (default: 60).", "default": 60},
        "priority": {"type": "string", "enum": ["normal", "low"], "description": "Filter by priority (omit for all)."},
    },
    "additionalProperties": False,
}


def list_events_handler(minutes: int = 60, priority: Optional[str] = None) -> List[Dict]:
    now = int(time.time())
    return DatadogClient().list_events(start=now - minutes * 60, end=now, priority=priority)


# ── datadog_create_event ──────────────────────────────────────────────────────

CREATE_EVENT_TOOL_NAME = "datadog_create_event"
CREATE_EVENT_TOOL_DESCRIPTION = (
    "Post a custom event to the Datadog event stream. "
    "Useful for marking deployments, incidents, or config changes."
)
CREATE_EVENT_TOOL_INPUT_SCHEMA: Dict[str, Any] = {
    "type": "object",
    "properties": {
        "title": {"type": "string", "description": "Event title."},
        "text": {"type": "string", "description": "Event body text."},
        "tags": {"type": "array", "items": {"type": "string"}, "description": "List of tags (e.g. ['env:prod', 'service:api'])."},
        "priority": {"type": "string", "enum": ["normal", "low"], "default": "normal", "description": "Event priority."},
    },
    "required": ["title", "text"],
    "additionalProperties": False,
}


def create_event_handler(title: str, text: str, tags: Optional[List[str]] = None, priority: str = "normal") -> Dict:
    return DatadogClient().create_event(title, text, tags=tags, priority=priority)


# ── datadog_list_dashboards ───────────────────────────────────────────────────

LIST_DASHBOARDS_TOOL_NAME = "datadog_list_dashboards"
LIST_DASHBOARDS_TOOL_DESCRIPTION = "List all Datadog dashboards with their IDs and URLs."
LIST_DASHBOARDS_TOOL_INPUT_SCHEMA: Dict[str, Any] = {
    "type": "object",
    "properties": {},
    "additionalProperties": False,
}


def list_dashboards_handler() -> List[Dict]:
    return DatadogClient().list_dashboards()


# ── datadog_list_incidents ────────────────────────────────────────────────────

LIST_INCIDENTS_TOOL_NAME = "datadog_list_incidents"
LIST_INCIDENTS_TOOL_DESCRIPTION = "List active Datadog incidents with severity and status."
LIST_INCIDENTS_TOOL_INPUT_SCHEMA: Dict[str, Any] = {
    "type": "object",
    "properties": {},
    "additionalProperties": False,
}


def list_incidents_handler() -> List[Dict]:
    return DatadogClient().list_incidents()


# ── datadog_list_hosts ────────────────────────────────────────────────────────

LIST_HOSTS_TOOL_NAME = "datadog_list_hosts"
LIST_HOSTS_TOOL_DESCRIPTION = (
    "List hosts reporting to Datadog. "
    "Optionally filter using a Datadog search string (e.g. 'env:prod')."
)
LIST_HOSTS_TOOL_INPUT_SCHEMA: Dict[str, Any] = {
    "type": "object",
    "properties": {
        "filter": {"type": "string", "description": "Datadog host search filter string (optional)."},
    },
    "additionalProperties": False,
}


def list_hosts_handler(filter: Optional[str] = None) -> List[Dict]:
    return DatadogClient().list_hosts(filter_str=filter)
