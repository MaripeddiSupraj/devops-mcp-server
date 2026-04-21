"""
integrations/vault_client.py
-----------------------------
HTTP client for HashiCorp Vault KV v2 secrets engine.

Required environment variables:
  VAULT_ADDR   — e.g. https://vault.example.com:8200
  VAULT_TOKEN  — root or service token with appropriate policy

Optional:
  VAULT_NAMESPACE  — for HCP Vault or Enterprise namespaces
  VAULT_MOUNT      — KV mount path (default: secret)
"""

from __future__ import annotations

import os
from typing import Any, Dict, List, Optional

from core.logger import get_logger

log = get_logger(__name__)


class VaultClientError(RuntimeError):
    """Wraps Vault API errors."""


def _get_config() -> tuple[str, str, str, str]:
    addr = os.environ.get("VAULT_ADDR", "").rstrip("/")
    token = os.environ.get("VAULT_TOKEN", "")
    namespace = os.environ.get("VAULT_NAMESPACE", "")
    mount = os.environ.get("VAULT_MOUNT", "secret")
    if not addr or not token:
        raise VaultClientError("VAULT_ADDR and VAULT_TOKEN must be set.")
    return addr, token, namespace, mount


class VaultClient:
    """HashiCorp Vault KV v2 client."""

    def __init__(self) -> None:
        import httpx
        self._addr, token, namespace, self._mount = _get_config()
        headers: Dict[str, str] = {"X-Vault-Token": token}
        if namespace:
            headers["X-Vault-Namespace"] = namespace
        self._http = httpx.Client(headers=headers, timeout=15)

    def _request(self, method: str, path: str, body: Optional[Dict] = None) -> Any:
        import httpx
        try:
            fn = getattr(self._http, method)
            resp = fn(f"{self._addr}/v1{path}", json=body)
            resp.raise_for_status()
            return resp.json() if resp.content else {}
        except httpx.HTTPStatusError as exc:
            raise VaultClientError(f"Vault API {exc.response.status_code}: {exc.response.text}") from exc
        except Exception as exc:
            raise VaultClientError(f"Vault request failed: {exc}") from exc

    def read_secret(self, path: str) -> Dict[str, Any]:
        data = self._request("get", f"/{self._mount}/data/{path.lstrip('/')}")
        secret_data = data.get("data", {}).get("data", {})
        metadata = data.get("data", {}).get("metadata", {})
        log.info("vault_secret_read", path=path)
        return {"path": path, "data": secret_data, "version": metadata.get("version"), "created_time": metadata.get("created_time")}

    def write_secret(self, path: str, data: Dict[str, str]) -> Dict[str, Any]:
        resp = self._request("post", f"/{self._mount}/data/{path.lstrip('/')}", {"data": data})
        version = resp.get("data", {}).get("version")
        log.info("vault_secret_written", path=path, version=version)
        return {"path": path, "version": version, "keys": list(data.keys())}

    def list_secrets(self, path: str) -> List[str]:
        try:
            data = self._request("list", f"/{self._mount}/metadata/{path.lstrip('/')}")
            return data.get("data", {}).get("keys", [])
        except VaultClientError as exc:
            if "404" in str(exc):
                return []
            raise
