"""integrations/scanner_runner.py — Trivy and tfsec CLI subprocess wrappers."""

from __future__ import annotations

import json
import subprocess
from typing import Any, Dict, List, Optional

from core.config import get_settings


class TrivyRunner:
    def __init__(self) -> None:
        cfg = get_settings()
        self._bin = cfg.trivy_binary
        self._timeout = cfg.scanner_timeout_seconds

    def _run(self, args: List[str]) -> str:
        cmd = [self._bin] + args
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=self._timeout)
        if result.returncode not in (0, 1):  # trivy exits 1 when vulnerabilities found
            raise RuntimeError(result.stderr.strip() or result.stdout.strip())
        return result.stdout.strip()

    def scan_image(self, image: str, severity: Optional[str] = None) -> Dict[str, Any]:
        args = ["image", "--format", "json", "--quiet"]
        if severity:
            args += ["--severity", severity]
        args.append(image)
        output = self._run(args)
        try:
            data = json.loads(output)
        except json.JSONDecodeError:
            return {"image": image, "raw": output}
        results = []
        for result in data.get("Results", []):
            vulns = result.get("Vulnerabilities") or []
            results.append({
                "target": result.get("Target"),
                "type": result.get("Type"),
                "vulnerability_count": len(vulns),
                "vulnerabilities": [
                    {
                        "id": v.get("VulnerabilityID"),
                        "package": v.get("PkgName"),
                        "installed": v.get("InstalledVersion"),
                        "fixed": v.get("FixedVersion"),
                        "severity": v.get("Severity"),
                        "title": v.get("Title"),
                    }
                    for v in vulns[:50]  # cap at 50 per target
                ],
            })
        return {"image": image, "results": results}

    def scan_filesystem(self, path: str, severity: Optional[str] = None) -> Dict[str, Any]:
        args = ["fs", "--format", "json", "--quiet"]
        if severity:
            args += ["--severity", severity]
        args.append(path)
        output = self._run(args)
        try:
            data = json.loads(output)
        except json.JSONDecodeError:
            return {"path": path, "raw": output}
        results = []
        for result in data.get("Results", []):
            vulns = result.get("Vulnerabilities") or []
            results.append({
                "target": result.get("Target"),
                "type": result.get("Type"),
                "vulnerability_count": len(vulns),
                "vulnerabilities": [
                    {
                        "id": v.get("VulnerabilityID"),
                        "package": v.get("PkgName"),
                        "severity": v.get("Severity"),
                        "title": v.get("Title"),
                    }
                    for v in vulns[:50]
                ],
            })
        return {"path": path, "results": results}


class TfsecRunner:
    def __init__(self) -> None:
        cfg = get_settings()
        self._bin = cfg.tfsec_binary
        self._timeout = cfg.scanner_timeout_seconds

    def _run(self, args: List[str]) -> str:
        cmd = [self._bin] + args
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=self._timeout)
        if result.returncode not in (0, 1):
            raise RuntimeError(result.stderr.strip() or result.stdout.strip())
        return result.stdout.strip()

    def scan(self, path: str, severity: Optional[str] = None) -> Dict[str, Any]:
        args = ["--format", "json", "--soft-fail"]
        if severity:
            args += ["--minimum-severity", severity]
        args.append(path)
        output = self._run(args)
        try:
            data = json.loads(output)
        except json.JSONDecodeError:
            return {"path": path, "raw": output}
        results = data.get("results", [])
        return {
            "path": path,
            "issue_count": len(results),
            "issues": [
                {
                    "rule_id": r.get("rule_id"),
                    "severity": r.get("severity"),
                    "description": r.get("description"),
                    "impact": r.get("impact"),
                    "resolution": r.get("resolution"),
                    "location": r.get("location"),
                }
                for r in results[:100]
            ],
        }
