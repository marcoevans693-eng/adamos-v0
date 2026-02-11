"""adam_os.memory.records

Build deterministic memory records for Phase 5 JSONL stores.

This module enforces:
- a stable, explicit record schema
- deterministic memory_id generation (no randomness)
- canonical hashing over fields excluding "hash"

Record schema (v0):
- memory_id: str
- type: str                  # episodic | procedural | semantic (or other explicit string)
- source: str                # caller-provided provenance string
- tags: list[str]            # optional labels
- text: str                  # primary content
- refs: list[dict]           # optional structured references
- created_at_utc: str        # ISO 8601 UTC timestamp (Z)
- hash: str                  # sha256 over canonical fields excluding hash
"""

from __future__ import annotations

import datetime as _dt
from typing import Any, Dict, List, Optional

from .canonical import canonical_dumps, hash_record_fields


class RecordError(ValueError):
    """Raised when record inputs violate schema requirements."""


def _utc_now_iso_z() -> str:
    now = _dt.datetime.now(tz=_dt.timezone.utc)
    # seconds precision is enough and stable; avoid microseconds to reduce churn
    return now.replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _require_str(name: str, value: Any, *, allow_empty: bool = False) -> str:
    if not isinstance(value, str):
        raise TypeError(f"{name} must be str")
    if not allow_empty and value.strip() == "":
        raise RecordError(f"{name} must be non-empty")
    return value


def _require_list_of_str(name: str, value: Any) -> List[str]:
    if value is None:
        return []
    if not isinstance(value, list):
        raise TypeError(f"{name} must be list[str]")
    out: List[str] = []
    for i, item in enumerate(value):
        if not isinstance(item, str):
            raise TypeError(f"{name}[{i}] must be str")
        s = item.strip()
        if s == "":
            continue
        out.append(s)
    return out


def _require_list_of_dict(name: str, value: Any) -> List[Dict[str, Any]]:
    if value is None:
        return []
    if not isinstance(value, list):
        raise TypeError(f"{name} must be list[dict]")
    out: List[Dict[str, Any]] = []
    for i, item in enumerate(value):
        if not isinstance(item, dict):
            raise TypeError(f"{name}[{i}] must be dict")
        out.append(item)
    return out


def _normalize_created_at(created_at_utc: Optional[str]) -> str:
    if created_at_utc is None:
        return _utc_now_iso_z()
    s = _require_str("created_at_utc", created_at_utc)
    # Minimal validation: must end with 'Z' and be parseable by fromisoformat after normalization.
    if not s.endswith("Z"):
        raise RecordError("created_at_utc must be UTC ISO string ending with 'Z'")
    try:
        _dt.datetime.fromisoformat(s.replace("Z", "+00:00"))
    except ValueError:
        raise RecordError("created_at_utc must be valid ISO 8601 UTC timestamp") from None
    return s


def _deterministic_memory_id(record_type: str, source: str, text: str, created_at_utc: str, tags: List[str], refs: List[Dict[str, Any]]) -> str:
    # Stable ID derived from canonical content fields.
    base = {
        "type": record_type,
        "source": source,
        "text": text,
        "created_at_utc": created_at_utc,
        "tags": tags,
        "refs": refs,
    }
    # Hash canonical JSON -> use prefix for readability.
    digest = hash_record_fields(base)
    return f"mem_{record_type}_{digest[:16]}"


def build_memory_record(
    record_type: str,
    source: str,
    tags: Optional[List[str]],
    text: str,
    refs: Optional[List[Dict[str, Any]]],
    created_at_utc: Optional[str] = None,
    memory_id: Optional[str] = None,
) -> Dict[str, Any]:
    """Build a deterministic, schema-valid memory record dict ready for JSONL append."""
    record_type = _require_str("type", record_type)
    source = _require_str("source", source)
    text = _require_str("text", text)

    norm_tags = _require_list_of_str("tags", tags)
    norm_refs = _require_list_of_dict("refs", refs)
    created = _normalize_created_at(created_at_utc)

    if memory_id is None:
        mid = _deterministic_memory_id(record_type, source, text, created, norm_tags, norm_refs)
    else:
        mid = _require_str("memory_id", memory_id)

    record_wo_hash: Dict[str, Any] = {
        "memory_id": mid,
        "type": record_type,
        "source": source,
        "tags": norm_tags,
        "text": text,
        "refs": norm_refs,
        "created_at_utc": created,
    }

    # Ensure canonicalization succeeds deterministically before hashing.
    _ = canonical_dumps(record_wo_hash)

    rec_hash = hash_record_fields(record_wo_hash)
    record = dict(record_wo_hash)
    record["hash"] = rec_hash
    return record


__all__ = [
    "RecordError",
    "build_memory_record",
]
