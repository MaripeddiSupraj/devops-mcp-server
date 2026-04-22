"""integrations/cloudflare_client.py — Cloudflare REST API v4 client (httpx)."""

from __future__ import annotations

from typing import Any, Dict, List, Optional

import httpx

from core.config import get_settings

_BASE = "https://api.cloudflare.com/client/v4"


class CloudflareClient:
    def __init__(self) -> None:
        cfg = get_settings()
        self._token = cfg.cloudflare_api_token
        self._account_id = cfg.cloudflare_account_id
        if not self._token:
            raise ValueError("CLOUDFLARE_API_TOKEN must be set.")
        self._headers = {"Authorization": f"Bearer {self._token}", "Content-Type": "application/json"}

    def _get(self, path: str, params: Optional[Dict] = None) -> Any:
        with httpx.Client(timeout=30) as client:
            r = client.get(f"{_BASE}{path}", headers=self._headers, params=params)
            r.raise_for_status()
            data = r.json()
            if not data.get("success"):
                raise RuntimeError(str(data.get("errors")))
            return data.get("result")

    def _post(self, path: str, body: Dict) -> Any:
        with httpx.Client(timeout=30) as client:
            r = client.post(f"{_BASE}{path}", headers=self._headers, json=body)
            r.raise_for_status()
            data = r.json()
            if not data.get("success"):
                raise RuntimeError(str(data.get("errors")))
            return data.get("result")

    def _delete(self, path: str) -> Any:
        with httpx.Client(timeout=30) as client:
            r = client.delete(f"{_BASE}{path}", headers=self._headers)
            r.raise_for_status()
            data = r.json()
            if not data.get("success"):
                raise RuntimeError(str(data.get("errors")))
            return data.get("result")

    def list_zones(self) -> List[Dict]:
        data = self._get("/zones", params={"per_page": 50})
        return [{"id": z["id"], "name": z["name"], "status": z["status"]} for z in (data or [])]

    def list_dns_records(self, zone_id: str, record_type: Optional[str] = None) -> List[Dict]:
        params: Dict[str, Any] = {"per_page": 100}
        if record_type:
            params["type"] = record_type
        data = self._get(f"/zones/{zone_id}/dns_records", params=params)
        return [
            {
                "id": r["id"],
                "type": r["type"],
                "name": r["name"],
                "content": r["content"],
                "proxied": r.get("proxied"),
                "ttl": r.get("ttl"),
            }
            for r in (data or [])
        ]

    def create_dns_record(self, zone_id: str, record_type: str, name: str, content: str, ttl: int = 1, proxied: bool = False) -> Dict:
        return self._post(f"/zones/{zone_id}/dns_records", {
            "type": record_type,
            "name": name,
            "content": content,
            "ttl": ttl,
            "proxied": proxied,
        })

    def delete_dns_record(self, zone_id: str, record_id: str) -> Dict:
        return self._delete(f"/zones/{zone_id}/dns_records/{record_id}")

    def purge_cache(self, zone_id: str, urls: Optional[List[str]] = None) -> Dict:
        body: Dict[str, Any] = {}
        if urls:
            body["files"] = urls
        else:
            body["purge_everything"] = True
        return self._post(f"/zones/{zone_id}/purge_cache", body)

    def list_waf_rules(self, zone_id: str) -> List[Dict]:
        data = self._get(f"/zones/{zone_id}/firewall/rules", params={"per_page": 100})
        return [
            {
                "id": r["id"],
                "description": r.get("description"),
                "action": r.get("action"),
                "paused": r.get("paused"),
            }
            for r in (data or [])
        ]
