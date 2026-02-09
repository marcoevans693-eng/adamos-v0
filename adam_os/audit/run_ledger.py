"""
Append-only Run Ledger (JSONL)

Purpose
- Provide a minimal, auditable, append-only event log for every "run".
- Write one JSON object per line (JSONL) so logs are streamable and greppable.
- No network, no databases, no framework coupling.

Contract
- Each event is an object with:
  - ts_utc: ISO8601 UTC timestamp string
  - run_id: caller-provided or created run id
  - seq: monotonically increasing integer per RunLedger instance
  - kind: short event type string (e.g., "run.start", "tool.call", "run.end")
  - data: arbitrary JSON-serializable dict payload

Storage
- Default directory: ./.adam_os/runs/
- Default file:     ./.adam_os/runs/<run_id>.jsonl
- Override base dir via env: ADAMOS_RUN_DIR
"""

from __future__ import annotations

import json
import os
import threading
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional


def _ts_utc() -> str:
    # ISO8601 in UTC, stable and explicit
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def new_run_id() -> str:
    # Unique run ids; not intended to be deterministic across executions.
    return uuid.uuid4().hex


def default_run_dir() -> Path:
    # Repo-local by default; overridable for VPS or centralized storage later.
    base = os.environ.get("ADAMOS_RUN_DIR", ".adam_os/runs")
    return Path(base)


@dataclass(frozen=True)
class LedgerPaths:
    run_dir: Path
    run_file: Path


def resolve_paths(run_id: str, run_dir: Optional[Path] = None) -> LedgerPaths:
    rd = run_dir or default_run_dir()
    rf = rd / f"{run_id}.jsonl"
    return LedgerPaths(run_dir=rd, run_file=rf)


class RunLedger:
    """
    Append-only JSONL writer for a single run_id.
    Thread-safe within a process.
    """

    def __init__(self, run_id: Optional[str] = None, run_dir: Optional[Path] = None) -> None:
        self.run_id = run_id or new_run_id()
        self.paths = resolve_paths(self.run_id, run_dir=run_dir)

        # Ensure directory exists (minimal side effect, required for writes).
        self.paths.run_dir.mkdir(parents=True, exist_ok=True)

        self._lock = threading.Lock()
        self._seq = 0

    def event(self, kind: str, data: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Append a single event line to the run file.
        Returns the event dict written (for caller echo/testing).
        """
        if not isinstance(kind, str) or not kind.strip():
            raise ValueError("kind must be a non-empty string")

        payload: Dict[str, Any] = {
            "ts_utc": _ts_utc(),
            "run_id": self.run_id,
            "seq": None,  # filled under lock
            "kind": kind.strip(),
            "data": data or {},
        }

        line = None
        with self._lock:
            self._seq += 1
            payload["seq"] = self._seq
            line = json.dumps(payload, ensure_ascii=False, separators=(",", ":")) + "\n"
            _append_text_atomic(self.paths.run_file, line)

        return payload

    def start(self, data: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        return self.event("run.start", data=data)

    def end(self, data: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        return self.event("run.end", data=data)


def _append_text_atomic(path: Path, text: str) -> None:
    """
    Best-effort durable append:
    - open with O_APPEND so each write is appended
    - write bytes, flush, fsync
    """
    flags = os.O_WRONLY | os.O_CREAT | os.O_APPEND
    fd = os.open(str(path), flags, 0o644)
    try:
        b = text.encode("utf-8")
        os.write(fd, b)
        os.fsync(fd)
    finally:
        os.close(fd)
