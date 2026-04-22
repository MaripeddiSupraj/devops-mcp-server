"""integrations/gitlab_client.py — GitLab REST API v4 client (httpx)."""

from __future__ import annotations

from typing import Any, Dict, List, Optional
from urllib.parse import quote

import httpx

from core.config import get_settings


class GitLabClient:
    def __init__(self) -> None:
        cfg = get_settings()
        self._token = cfg.gitlab_token
        self._url = cfg.gitlab_url.rstrip("/")
        if not self._token:
            raise ValueError("GITLAB_TOKEN must be set.")
        self._headers = {"PRIVATE-TOKEN": self._token, "Content-Type": "application/json"}

    def _get(self, path: str, params: Optional[Dict] = None) -> Any:
        with httpx.Client(timeout=30) as client:
            r = client.get(f"{self._url}/api/v4{path}", headers=self._headers, params=params)
            r.raise_for_status()
            return r.json()

    def _post(self, path: str, body: Dict) -> Any:
        with httpx.Client(timeout=30) as client:
            r = client.post(f"{self._url}/api/v4{path}", headers=self._headers, json=body)
            r.raise_for_status()
            return r.json()

    def _put(self, path: str, body: Dict) -> Any:
        with httpx.Client(timeout=30) as client:
            r = client.put(f"{self._url}/api/v4{path}", headers=self._headers, json=body)
            r.raise_for_status()
            return r.json()

    def list_projects(self, search: Optional[str] = None, limit: int = 20) -> List[Dict]:
        params: Dict[str, Any] = {"per_page": limit, "order_by": "last_activity_at"}
        if search:
            params["search"] = search
        data = self._get("/projects", params=params)
        return [
            {
                "id": p["id"],
                "name": p["name"],
                "path": p["path_with_namespace"],
                "url": p["web_url"],
                "default_branch": p.get("default_branch"),
                "last_activity": p.get("last_activity_at"),
            }
            for p in data
        ]

    def list_merge_requests(self, project_id: str, state: str = "opened") -> List[Dict]:
        pid = quote(str(project_id), safe="")
        data = self._get(f"/projects/{pid}/merge_requests", params={"state": state, "per_page": 50})
        return [
            {
                "iid": mr["iid"],
                "title": mr["title"],
                "state": mr["state"],
                "author": mr["author"]["username"],
                "source_branch": mr["source_branch"],
                "target_branch": mr["target_branch"],
                "url": mr["web_url"],
            }
            for mr in data
        ]

    def create_merge_request(self, project_id: str, title: str, source_branch: str, target_branch: str, description: str = "") -> Dict:
        pid = quote(str(project_id), safe="")
        return self._post(f"/projects/{pid}/merge_requests", {
            "title": title,
            "source_branch": source_branch,
            "target_branch": target_branch,
            "description": description,
        })

    def merge_mr(self, project_id: str, mr_iid: int) -> Dict:
        pid = quote(str(project_id), safe="")
        return self._put(f"/projects/{pid}/merge_requests/{mr_iid}/merge", {})

    def list_pipelines(self, project_id: str, status: Optional[str] = None) -> List[Dict]:
        pid = quote(str(project_id), safe="")
        params: Dict[str, Any] = {"per_page": 20}
        if status:
            params["status"] = status
        data = self._get(f"/projects/{pid}/pipelines", params=params)
        return [
            {
                "id": p["id"],
                "status": p["status"],
                "ref": p["ref"],
                "sha": p["sha"],
                "created_at": p.get("created_at"),
                "web_url": p.get("web_url"),
            }
            for p in data
        ]

    def trigger_pipeline(self, project_id: str, ref: str) -> Dict:
        pid = quote(str(project_id), safe="")
        return self._post(f"/projects/{pid}/pipeline", {"ref": ref})

    def list_issues(self, project_id: str, state: str = "opened") -> List[Dict]:
        pid = quote(str(project_id), safe="")
        data = self._get(f"/projects/{pid}/issues", params={"state": state, "per_page": 50})
        return [
            {
                "iid": i["iid"],
                "title": i["title"],
                "state": i["state"],
                "author": i["author"]["username"],
                "labels": i.get("labels", []),
                "url": i["web_url"],
            }
            for i in data
        ]
