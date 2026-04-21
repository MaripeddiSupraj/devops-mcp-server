"""
integrations/pagerduty_client.py
----------------------------------
HTTP client for the PagerDuty REST API v2.

Required environment variables:
  PAGERDUTY_API_KEY    — REST API key (Account > API Access > Create New API Key)

Optional:
  PAGERDUTY_EMAIL      — Required only for actions that need a From header (create incident).
  PAGERDUTY_SERVICE_ID — Default service ID for creating incidents.
"""

from __future__ import annotations

import os
from typing import Any, Dict, List, Optional

from core.logger import get_logger

log = get_logger(__name__)

_PD_BASE = "https://api.pagerduty.com"


class PagerDutyClientError(RuntimeError):
    """Wraps PagerDuty API errors."""


def _get_config() -> tuple[str, str, str]:
    api_key = os.environ.get("PAGERDUTY_API_KEY", "")
    email = os.environ.get("PAGERDUTY_EMAIL", "")
    service_id = os.environ.get("PAGERDUTY_SERVICE_ID", "")
    if not api_key:
        raise PagerDutyClientError("PAGERDUTY_API_KEY must be set.")
    return api_key, email, service_id


class PagerDutyClient:
    """PagerDuty REST API v2 client."""

    def __init__(self) -> None:
        import httpx
        api_key, self._email, self._service_id = _get_config()
        self._http = httpx.Client(
            headers={
                "Authorization": f"Token token={api_key}",
                "Accept": "application/vnd.pagerduty+json;version=2",
                "Content-Type": "application/json",
            },
            timeout=15,
        )

    def _get(self, path: str, params: Optional[Dict] = None) -> Any:
        import httpx
        try:
            resp = self._http.get(f"{_PD_BASE}{path}", params=params)
            resp.raise_for_status()
            return resp.json()
        except httpx.HTTPStatusError as exc:
            raise PagerDutyClientError(f"PagerDuty API {exc.response.status_code}: {exc.response.text}") from exc

    def _put(self, path: str, body: Dict) -> Any:
        import httpx
        try:
            resp = self._http.put(f"{_PD_BASE}{path}", json=body)
            resp.raise_for_status()
            return resp.json()
        except httpx.HTTPStatusError as exc:
            raise PagerDutyClientError(f"PagerDuty API {exc.response.status_code}: {exc.response.text}") from exc

    def _post(self, path: str, body: Dict) -> Any:
        import httpx
        try:
            headers = {}
            if self._email:
                headers["From"] = self._email
            resp = self._http.post(f"{_PD_BASE}{path}", json=body, headers=headers)
            resp.raise_for_status()
            return resp.json()
        except httpx.HTTPStatusError as exc:
            raise PagerDutyClientError(f"PagerDuty API {exc.response.status_code}: {exc.response.text}") from exc

    def list_incidents(self, status: Optional[str] = None, limit: int = 25) -> List[Dict[str, Any]]:
        params: Dict[str, Any] = {"limit": limit, "sort_by": "created_at:desc"}
        if status:
            params["statuses[]"] = status
        data = self._get("/incidents", params=params)
        return [
            {
                "id": inc["id"],
                "title": inc["title"],
                "status": inc["status"],
                "urgency": inc["urgency"],
                "service": inc["service"]["summary"],
                "created_at": inc["created_at"],
                "html_url": inc["html_url"],
                "assignees": [a["assignee"]["summary"] for a in inc.get("assignments", [])],
            }
            for inc in data.get("incidents", [])
        ]

    def acknowledge_incident(self, incident_id: str) -> Dict[str, Any]:
        body = {"incident": {"type": "incident_reference", "status": "acknowledged"}}
        data = self._put(f"/incidents/{incident_id}", body)
        log.info("pagerduty_incident_acknowledged", id=incident_id)
        return {"id": incident_id, "status": data["incident"]["status"]}

    def resolve_incident(self, incident_id: str) -> Dict[str, Any]:
        body = {"incident": {"type": "incident_reference", "status": "resolved"}}
        data = self._put(f"/incidents/{incident_id}", body)
        log.info("pagerduty_incident_resolved", id=incident_id)
        return {"id": incident_id, "status": data["incident"]["status"]}

    def create_incident(self, title: str, service_id: Optional[str] = None, urgency: str = "high", body: str = "") -> Dict[str, Any]:
        svc = service_id or self._service_id
        if not svc:
            raise PagerDutyClientError("service_id must be provided or PAGERDUTY_SERVICE_ID must be set.")
        payload: Dict[str, Any] = {
            "incident": {
                "type": "incident",
                "title": title,
                "service": {"id": svc, "type": "service_reference"},
                "urgency": urgency,
            }
        }
        if body:
            payload["incident"]["body"] = {"type": "incident_body", "details": body}
        data = self._post("/incidents", payload)
        inc = data["incident"]
        log.info("pagerduty_incident_created", id=inc["id"], title=title)
        return {"id": inc["id"], "title": inc["title"], "status": inc["status"], "html_url": inc["html_url"]}
