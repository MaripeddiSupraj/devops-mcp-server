"""integrations/datadog_client.py — Datadog REST API v1/v2 client (httpx)."""

from __future__ import annotations

from typing import Any, Dict, List, Optional

import httpx

from core.config import get_settings


class DatadogClient:
    def __init__(self) -> None:
        cfg = get_settings()
        self._api_key = cfg.datadog_api_key
        self._app_key = cfg.datadog_app_key
        self._site = cfg.datadog_site  # e.g. datadoghq.com or datadoghq.eu
        if not self._api_key or not self._app_key:
            raise ValueError("DATADOG_API_KEY and DATADOG_APP_KEY must be set.")
        self._base_v1 = f"https://api.{self._site}/api/v1"
        self._base_v2 = f"https://api.{self._site}/api/v2"
        self._headers = {
            "DD-API-KEY": self._api_key,
            "DD-APPLICATION-KEY": self._app_key,
            "Content-Type": "application/json",
        }

    def _get(self, url: str, params: Optional[Dict] = None) -> Any:
        with httpx.Client(timeout=30) as client:
            r = client.get(url, headers=self._headers, params=params)
            r.raise_for_status()
            return r.json()

    def _post(self, url: str, body: Dict) -> Any:
        with httpx.Client(timeout=30) as client:
            r = client.post(url, headers=self._headers, json=body)
            r.raise_for_status()
            return r.json()

    def _patch(self, url: str, body: Dict) -> Any:
        with httpx.Client(timeout=30) as client:
            r = client.patch(url, headers=self._headers, json=body)
            r.raise_for_status()
            return r.json()

    # ── Monitors ──────────────────────────────────────────────────────────────

    def list_monitors(self, status: Optional[str] = None) -> List[Dict]:
        params = {}
        if status:
            params["monitor_status"] = status
        data = self._get(f"{self._base_v1}/monitor", params=params or None)
        return [
            {
                "id": m["id"],
                "name": m["name"],
                "type": m["type"],
                "status": m.get("overall_state", "unknown"),
                "message": m.get("message", ""),
                "tags": m.get("tags", []),
            }
            for m in (data if isinstance(data, list) else [])
        ]

    def mute_monitor(self, monitor_id: int, end: Optional[str] = None) -> Dict:
        body: Dict[str, Any] = {}
        if end:
            body["end"] = end
        return self._post(f"{self._base_v1}/monitor/{monitor_id}/mute", body)

    def unmute_monitor(self, monitor_id: int) -> Dict:
        return self._post(f"{self._base_v1}/monitor/{monitor_id}/unmute", {})

    # ── Metrics ───────────────────────────────────────────────────────────────

    def query_metrics(self, query: str, from_ts: int, to_ts: int) -> Dict:
        return self._get(
            f"{self._base_v1}/query",
            params={"query": query, "from": from_ts, "to": to_ts},
        )

    # ── Events ────────────────────────────────────────────────────────────────

    def list_events(self, start: int, end: int, priority: Optional[str] = None) -> List[Dict]:
        params: Dict[str, Any] = {"start": start, "end": end}
        if priority:
            params["priority"] = priority
        data = self._get(f"{self._base_v1}/events", params=params)
        return data.get("events", [])

    def create_event(self, title: str, text: str, tags: Optional[List[str]] = None, priority: str = "normal") -> Dict:
        body: Dict[str, Any] = {"title": title, "text": text, "priority": priority}
        if tags:
            body["tags"] = tags
        return self._post(f"{self._base_v1}/events", body)

    # ── Dashboards ────────────────────────────────────────────────────────────

    def list_dashboards(self) -> List[Dict]:
        data = self._get(f"{self._base_v1}/dashboard")
        return [
            {"id": d["id"], "title": d["title"], "url": d.get("url", "")}
            for d in data.get("dashboards", [])
        ]

    # ── Incidents ─────────────────────────────────────────────────────────────

    def list_incidents(self) -> List[Dict]:
        data = self._get(f"{self._base_v2}/incidents")
        return [
            {
                "id": inc["id"],
                "title": inc["attributes"].get("title"),
                "status": inc["attributes"].get("status"),
                "severity": inc["attributes"].get("severity"),
                "created": inc["attributes"].get("created"),
            }
            for inc in data.get("data", [])
        ]

    # ── Service checks / hosts ────────────────────────────────────────────────

    def list_hosts(self, filter_str: Optional[str] = None) -> List[Dict]:
        params = {}
        if filter_str:
            params["filter"] = filter_str
        data = self._get(f"{self._base_v1}/hosts", params=params or None)
        return [
            {
                "id": h.get("id"),
                "name": h.get("host_name"),
                "status": h.get("up"),
                "tags": h.get("tags_by_source", {}),
            }
            for h in data.get("host_list", [])
        ]
