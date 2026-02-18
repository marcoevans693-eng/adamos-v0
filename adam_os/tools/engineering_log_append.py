"""adam_os.tools.engineering_log_append

Deterministic, append-only Engineering Activity Log writer.

Scope:
- Accept a structured dict event
- Validate required fields
- Append exactly one JSON line to .adam_os/engineering/activity_log.jsonl
- Return sha256 of the exact appended line bytes (including trailing \n)

Non-goals:
- No registry writes
- No inference calls
- No background behavior
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any, Dict, Iterable


DEFAULT_ACTIVITY_LOG_PATH = Path(".adam_os/engineering/activity_log.jsonl")


class EngineeringLogValidationError(ValueError):
    """Raised when an event payload fails validation."""


def _require_keys(event: Dict[str, Any], keys: Iterable[str]) -> None:
    missing = [k for k in keys if k not in event]
    if missing:
        raise EngineeringLogValidationError(f"missing required field(s): {', '.join(missing)}")


def _validate_event(event: Dict[str, Any]) -> None:
    if not isinstance(event, dict):
        raise EngineeringLogValidationError("event must be a dict")

    # Minimal required fields for v0 of observability.
    _require_keys(event, ["created_at_utc", "event_type", "status"])

    if not isinstance(event.get("created_at_utc"), str) or not event["created_at_utc"].strip():
        raise EngineeringLogValidationError("created_at_utc must be a non-empty string")

    if not isinstance(event.get("event_type"), str) or not event["event_type"].strip():
        raise EngineeringLogValidationError("event_type must be a non-empty string")

    if not isinstance(event.get("status"), str) or not event["status"].strip():
        raise EngineeringLogValidationError("status must be a non-empty string")


def _canonical_json_line(event: Dict[str, Any]) -> str:
    # Deterministic serialization:
    # - sort_keys=True for stable key order
    # - separators=(',', ':') removes whitespace variance
    # - ensure_ascii=False preserves unicode deterministically in utf-8 bytes
    return json.dumps(event, sort_keys=True, separators=(",", ":"), ensure_ascii=False) + "\n"


def append_engineering_event(
    event: Dict[str, Any],
    log_path: Path = DEFAULT_ACTIVITY_LOG_PATH,
) -> str:
    """Append ONE event as ONE JSON line; return sha256 hex of the exact appended line bytes."""
    _validate_event(event)

    log_path = Path(log_path)
    log_path.parent.mkdir(parents=True, exist_ok=True)

    line = _canonical_json_line(event)
    b = line.encode("utf-8")

    with log_path.open("ab") as f:
        f.write(b)
        f.flush()

    return hashlib.sha256(b).hexdigest()
