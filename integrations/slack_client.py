"""
integrations/slack_client.py
-----------------------------
Slack notification client using incoming webhooks.

Configure via SLACK_WEBHOOK_URL environment variable. When not set,
all notification calls are silently skipped — no errors.

Usage:
    from integrations.slack_client import slack_notify
    slack_notify.tool_success("terraform_apply", {"workspace": "prod"}, duration_ms=4500)
    slack_notify.tool_failure("k8s_deploy", {"image": "nginx"}, error="timeout", duration_ms=60000)
"""

from __future__ import annotations

import json
from typing import Any, Dict, Optional

import httpx

from core.config import get_settings
from core.logger import get_logger

log = get_logger(__name__)

# Emoji status indicators
_ICONS = {
    "success": ":white_check_mark:",
    "error": ":x:",
    "warning": ":warning:",
    "info": ":information_source:",
}


class SlackNotifier:
    """Posts structured notifications to a Slack channel via incoming webhook."""

    def __init__(self) -> None:
        self._webhook: Optional[str] = None

    def _get_webhook(self) -> Optional[str]:
        if self._webhook is None:
            self._webhook = getattr(get_settings(), "slack_webhook_url", None) or ""
        return self._webhook or None

    # ── public helpers ────────────────────────────────────────────────────────

    def tool_success(
        self,
        tool_name: str,
        inputs: Dict[str, Any],
        duration_ms: int,
    ) -> None:
        """Post a success notification for a completed tool call."""
        self._post(
            icon=_ICONS["success"],
            title=f"Tool succeeded: `{tool_name}`",
            color="#36a64f",
            fields=[
                {"title": "Duration", "value": f"{duration_ms} ms", "short": True},
                {"title": "Inputs", "value": _summarise(inputs), "short": False},
            ],
        )

    def tool_failure(
        self,
        tool_name: str,
        inputs: Dict[str, Any],
        error: str,
        duration_ms: int,
    ) -> None:
        """Post a failure notification for a failed tool call."""
        self._post(
            icon=_ICONS["error"],
            title=f"Tool failed: `{tool_name}`",
            color="#d9534f",
            fields=[
                {"title": "Duration", "value": f"{duration_ms} ms", "short": True},
                {"title": "Error", "value": error[:500], "short": False},
                {"title": "Inputs", "value": _summarise(inputs), "short": False},
            ],
        )

    def alert(self, message: str, level: str = "info") -> None:
        """Post a freeform alert message."""
        icon = _ICONS.get(level, _ICONS["info"])
        color_map = {"error": "#d9534f", "warning": "#f0ad4e", "info": "#5bc0de", "success": "#36a64f"}
        self._post(
            icon=icon,
            title=message,
            color=color_map.get(level, "#5bc0de"),
            fields=[],
        )

    # ── internals ─────────────────────────────────────────────────────────────

    def _post(
        self,
        icon: str,
        title: str,
        color: str,
        fields: list,
    ) -> None:
        webhook = self._get_webhook()
        if not webhook:
            return  # Slack not configured — silent no-op

        payload = {
            "attachments": [
                {
                    "fallback": title,
                    "color": color,
                    "pretext": f"{icon} *DevOps MCP Server*",
                    "title": title,
                    "fields": fields,
                    "mrkdwn_in": ["pretext", "title", "fields"],
                }
            ]
        }

        try:
            resp = httpx.post(
                webhook,
                content=json.dumps(payload),
                headers={"Content-Type": "application/json"},
                timeout=5.0,
            )
            resp.raise_for_status()
        except Exception as exc:  # pylint: disable=broad-except
            # Never let Slack errors affect tool execution
            log.warning("slack_notify_failed", error=str(exc))


def _summarise(inputs: Dict[str, Any]) -> str:
    """Return a short single-line summary of tool inputs."""
    try:
        text = json.dumps(inputs, default=str)
        return text[:300] + "…" if len(text) > 300 else text
    except Exception:
        return str(inputs)[:300]


# Singleton
slack_notify = SlackNotifier()
