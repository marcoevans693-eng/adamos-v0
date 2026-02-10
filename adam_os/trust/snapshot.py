"""
Phase 4 — Execution Snapshot Collector

Pure observation.
No mutation.
No execution control.

Captures deterministic pre-run / post-run state for trust evaluation.
"""

from __future__ import annotations

import platform
import subprocess
from datetime import datetime, timezone
from typing import Dict, List


def _ts_utc() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _run(cmd: List[str]) -> str:
    """
    Run a command and return stdout (stripped).
    Never raises: failures return empty string.
    """
    try:
        out = subprocess.check_output(cmd, stderr=subprocess.DEVNULL)
        return out.decode("utf-8").strip()
    except Exception:
        return ""


def collect_snapshot(repo_root: str) -> Dict:
    """
    Collect a deterministic snapshot of execution-relevant state.
    Read-only. Best-effort.
    """

    branch = _run(["git", "branch", "--show-current"])
    head = _run(["git", "rev-parse", "HEAD"])
    porcelain = _run(["git", "status", "--porcelain=v1"])

    modified_files: List[str] = []
    untracked_files: List[str] = []

    if porcelain:
        for line in porcelain.splitlines():
            status = line[:2]
            path = line[3:].lstrip()
            if status == "??":
                untracked_files.append(path)
            else:
                modified_files.append(path)

    snapshot = {
        "timestamp_utc": _ts_utc(),
        "git": {
            "branch": branch,
            "head_commit": head,
            "is_clean": not bool(porcelain),
            "modified_files": modified_files,
            "untracked_files": untracked_files,
        },
        "fs": {
            "repo_root": repo_root,
        },
        "runtime": {
            "python_version": platform.python_version(),
            "platform": platform.platform(),
        },
    }

    return snapshot
