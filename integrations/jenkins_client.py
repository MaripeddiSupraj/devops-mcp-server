"""integrations/jenkins_client.py — Jenkins REST API client (httpx)."""

from __future__ import annotations

from typing import Any, Dict, List, Optional

import httpx

from core.config import get_settings


class JenkinsClient:
    def __init__(self) -> None:
        cfg = get_settings()
        self._url = cfg.jenkins_url
        self._user = cfg.jenkins_user
        self._token = cfg.jenkins_token
        if not self._url or not self._user or not self._token:
            raise ValueError("JENKINS_URL, JENKINS_USER, and JENKINS_TOKEN must be set.")
        self._auth = (self._user, self._token)

    def _get(self, path: str, params: Optional[Dict] = None) -> Any:
        with httpx.Client(timeout=30) as client:
            r = client.get(f"{self._url.rstrip('/')}{path}", auth=self._auth, params=params)
            r.raise_for_status()
            return r.json()

    def _post(self, path: str, params: Optional[Dict] = None) -> httpx.Response:
        with httpx.Client(timeout=30) as client:
            r = client.post(f"{self._url.rstrip('/')}{path}", auth=self._auth, params=params)
            r.raise_for_status()
            return r

    def list_jobs(self) -> List[Dict]:
        data = self._get("/api/json?tree=jobs[name,url,color]")
        return [
            {"name": j["name"], "url": j["url"], "status": j.get("color", "unknown")}
            for j in data.get("jobs", [])
        ]

    def get_job(self, job_name: str) -> Dict:
        data = self._get(f"/job/{job_name}/api/json")
        return {
            "name": data.get("name"),
            "url": data.get("url"),
            "buildable": data.get("buildable"),
            "last_build": data.get("lastBuild"),
            "last_successful_build": data.get("lastSuccessfulBuild"),
            "last_failed_build": data.get("lastFailedBuild"),
        }

    def get_build(self, job_name: str, build_number: int) -> Dict:
        data = self._get(f"/job/{job_name}/{build_number}/api/json")
        return {
            "number": data.get("number"),
            "result": data.get("result"),
            "duration_ms": data.get("duration"),
            "timestamp": data.get("timestamp"),
            "building": data.get("building"),
            "url": data.get("url"),
        }

    def trigger_build(self, job_name: str, params: Optional[Dict[str, str]] = None) -> Dict:
        if params:
            path = f"/job/{job_name}/buildWithParameters"
            self._post(path, params=params)
        else:
            self._post(f"/job/{job_name}/build")
        return {"job": job_name, "status": "triggered", "params": params or {}}

    def get_build_log(self, job_name: str, build_number: int) -> str:
        url = f"{self._url.rstrip('/')}/job/{job_name}/{build_number}/consoleText"
        with httpx.Client(timeout=60) as client:
            r = client.get(url, auth=self._auth)
            r.raise_for_status()
            return r.text

    def list_builds(self, job_name: str, limit: int = 10) -> List[Dict]:
        data = self._get(
            f"/job/{job_name}/api/json",
        )
        builds = data.get("builds", [])[:limit]
        results = []
        for b in builds:
            try:
                build = self._get(f"/job/{job_name}/{b['number']}/api/json")
                results.append({
                    "number": build.get("number"),
                    "result": build.get("result"),
                    "duration_ms": build.get("duration"),
                    "building": build.get("building"),
                })
            except Exception:
                results.append({"number": b.get("number"), "result": "unknown"})
        return results
