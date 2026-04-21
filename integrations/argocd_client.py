"""
integrations/argocd_client.py
------------------------------
HTTP client for the ArgoCD REST API.

Required environment variables:
  ARGOCD_SERVER_URL  — e.g. https://argocd.example.com
  ARGOCD_AUTH_TOKEN  — Bearer token (create with: argocd account generate-token)

TLS verification can be disabled with ARGOCD_INSECURE=true for self-signed certs.
"""

from __future__ import annotations

import os
from typing import Any, Dict, List, Optional

from core.logger import get_logger

log = get_logger(__name__)

_DEFAULT_TIMEOUT = 30


class ArgoCDClientError(RuntimeError):
    """Wraps ArgoCD API errors."""


def _get_config() -> tuple[str, str, bool]:
    url = os.environ.get("ARGOCD_SERVER_URL", "").rstrip("/")
    token = os.environ.get("ARGOCD_AUTH_TOKEN", "")
    insecure = os.environ.get("ARGOCD_INSECURE", "false").lower() == "true"
    if not url or not token:
        raise ArgoCDClientError(
            "ARGOCD_SERVER_URL and ARGOCD_AUTH_TOKEN must be set."
        )
    return url, token, insecure


class ArgoCDClient:
    """ArgoCD REST API client."""

    def __init__(self) -> None:
        import httpx
        self._url, token, insecure = _get_config()
        self._http = httpx.Client(
            headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
            verify=not insecure,
            timeout=_DEFAULT_TIMEOUT,
        )

    def _get(self, path: str, params: Optional[Dict] = None) -> Any:
        import httpx
        try:
            resp = self._http.get(f"{self._url}/api/v1{path}", params=params)
            resp.raise_for_status()
            return resp.json()
        except httpx.HTTPStatusError as exc:
            raise ArgoCDClientError(f"ArgoCD API error {exc.response.status_code}: {exc.response.text}") from exc
        except Exception as exc:
            raise ArgoCDClientError(f"ArgoCD request failed: {exc}") from exc

    def _post(self, path: str, body: Optional[Dict] = None) -> Any:
        import httpx
        try:
            resp = self._http.post(f"{self._url}/api/v1{path}", json=body or {})
            resp.raise_for_status()
            return resp.json()
        except httpx.HTTPStatusError as exc:
            raise ArgoCDClientError(f"ArgoCD API error {exc.response.status_code}: {exc.response.text}") from exc
        except Exception as exc:
            raise ArgoCDClientError(f"ArgoCD request failed: {exc}") from exc

    def list_apps(self) -> List[Dict[str, Any]]:
        data = self._get("/applications")
        return [
            {
                "name": app["metadata"]["name"],
                "namespace": app["metadata"].get("namespace"),
                "project": app["spec"].get("project"),
                "source_repo": app["spec"].get("source", {}).get("repoURL"),
                "source_path": app["spec"].get("source", {}).get("path"),
                "target_revision": app["spec"].get("source", {}).get("targetRevision"),
                "dest_namespace": app["spec"].get("destination", {}).get("namespace"),
                "dest_server": app["spec"].get("destination", {}).get("server"),
                "sync_status": app["status"].get("sync", {}).get("status"),
                "health_status": app["status"].get("health", {}).get("status"),
            }
            for app in data.get("items", [])
        ]

    def get_app(self, name: str) -> Dict[str, Any]:
        data = self._get(f"/applications/{name}")
        return {
            "name": data["metadata"]["name"],
            "sync_status": data["status"].get("sync", {}).get("status"),
            "health_status": data["status"].get("health", {}).get("status"),
            "revision": data["status"].get("sync", {}).get("revision"),
            "conditions": data["status"].get("conditions", []),
            "resources": [
                {
                    "kind": r.get("kind"),
                    "name": r.get("name"),
                    "namespace": r.get("namespace"),
                    "status": r.get("status"),
                    "health": r.get("health", {}).get("status"),
                }
                for r in data["status"].get("resources", [])
            ],
        }

    def sync_app(self, name: str, prune: bool = False, dry_run: bool = False) -> Dict[str, Any]:
        body: Dict[str, Any] = {"prune": prune, "dryRun": dry_run}
        self._post(f"/applications/{name}/sync", body)
        log.info("argocd_app_synced", name=name, prune=prune, dry_run=dry_run)
        return {"name": name, "action": "sync", "prune": prune, "dry_run": dry_run, "status": "sync_initiated"}

    def rollback_app(self, name: str, revision_id: int) -> Dict[str, Any]:
        self._post(f"/applications/{name}/rollback", {"id": revision_id})
        log.info("argocd_app_rolled_back", name=name, revision=revision_id)
        return {"name": name, "action": "rollback", "revision_id": revision_id, "status": "rollback_initiated"}
