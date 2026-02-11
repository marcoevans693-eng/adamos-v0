"""adam_os.memory.store

Append-only JSONL store utilities for Phase 5.

Contracts:
- One record per line (JSON object) with a trailing newline.
- Writes are append-only (no in-place edits).
- Read preserves file order (deterministic).
- Strict validation: record must be JSON-serializable and must contain required keys:
  memory_id, type, source, created_at_utc, hash
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List, Union


class StoreError(ValueError):
    """Raised when store operations or record validation fails."""


_REQUIRED_KEYS = ("memory_id", "type", "source", "created_at_utc", "hash")


def _validate_record(record: Dict[str, Any]) -> None:
    if not isinstance(record, dict):
        raise TypeError("record must be dict")
    for k in _REQUIRED_KEYS:
        if k not in record:
            raise StoreError(f"record missing required key: {k}")
    try:
        json.dumps(
            record,
            ensure_ascii=False,
            allow_nan=False,
            sort_keys=True,
            separators=(",", ":"),
        )
    except (TypeError, ValueError) as e:
        raise StoreError(f"record is not JSON-serializable: {e}") from None


def append_record(path: Union[str, Path], record: Dict[str, Any]) -> None:
    """Append a single record as one JSON line with trailing newline."""
    _validate_record(record)
    p = Path(path)

    if p.parent and not p.parent.exists():
        raise StoreError(f"parent directory does not exist: {p.parent}")

    line = json.dumps(
        record,
        ensure_ascii=False,
        allow_nan=False,
        sort_keys=True,
        separators=(",", ":"),
    )

    with p.open("a", encoding="utf-8") as f:
        f.write(line)
        f.write("\n")


def read_records(path: Union[str, Path]) -> List[Dict[str, Any]]:
    """Read records from a JSONL file in file order."""
    p = Path(path)
    if not p.exists():
        return []

    out: List[Dict[str, Any]] = []
    with p.open("r", encoding="utf-8") as f:
        for idx, raw in enumerate(f, start=1):
            s = raw.rstrip("\n")
            if s.strip() == "":
                continue
            try:
                obj = json.loads(s)
            except json.JSONDecodeError as e:
                raise StoreError(f"invalid JSON on line {idx}: {e}") from None
            if not isinstance(obj, dict):
                raise StoreError(f"non-object JSON on line {idx}")
            out.append(obj)

    return out


__all__ = [
    "StoreError",
    "append_record",
    "read_records",
]
