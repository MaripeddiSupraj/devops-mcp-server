"""integrations/docker_runner.py — Docker CLI subprocess wrapper."""

from __future__ import annotations

import json
import subprocess
from typing import Any, Dict, List, Optional

from core.config import get_settings


class DockerRunner:
    def __init__(self) -> None:
        cfg = get_settings()
        self._bin = cfg.docker_binary
        self._timeout = cfg.docker_timeout_seconds

    def _run(self, args: List[str]) -> str:
        cmd = [self._bin] + args
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=self._timeout,
        )
        if result.returncode != 0:
            raise RuntimeError(result.stderr.strip() or result.stdout.strip())
        return result.stdout.strip()

    def list_images(self, filter_ref: Optional[str] = None) -> List[Dict[str, Any]]:
        args = ["images", "--format", "{{json .}}"]
        if filter_ref:
            args.append(filter_ref)
        output = self._run(args)
        images = []
        for line in output.splitlines():
            if line.strip():
                try:
                    images.append(json.loads(line))
                except json.JSONDecodeError:
                    pass
        return images

    def pull(self, image: str) -> str:
        return self._run(["pull", image])

    def build(self, context: str, tag: str, dockerfile: Optional[str] = None, build_args: Optional[Dict[str, str]] = None) -> str:
        args = ["build", "-t", tag]
        if dockerfile:
            args += ["-f", dockerfile]
        if build_args:
            for k, v in build_args.items():
                args += ["--build-arg", f"{k}={v}"]
        args.append(context)
        return self._run(args)

    def push(self, image: str) -> str:
        return self._run(["push", image])

    def inspect(self, image: str) -> List[Dict[str, Any]]:
        output = self._run(["inspect", image])
        return json.loads(output)

    def list_containers(self, all_containers: bool = False) -> List[Dict[str, Any]]:
        args = ["ps", "--format", "{{json .}}"]
        if all_containers:
            args.insert(1, "-a")
        output = self._run(args)
        containers = []
        for line in output.splitlines():
            if line.strip():
                try:
                    containers.append(json.loads(line))
                except json.JSONDecodeError:
                    pass
        return containers

    def logs(self, container: str, tail: int = 100) -> str:
        return self._run(["logs", "--tail", str(tail), container])

    def tag(self, source: str, target: str) -> str:
        return self._run(["tag", source, target])

    def rmi(self, image: str, force: bool = False) -> str:
        args = ["rmi"]
        if force:
            args.append("-f")
        args.append(image)
        return self._run(args)
