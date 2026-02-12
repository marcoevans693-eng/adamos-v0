"""adam_os.memory.readers.jsonl_reader

Deterministic JSONL memory store reader for Phase 6.

Contracts:
- Read-only. No writes. No ledger.
- Deterministic store iteration: store_paths sorted lexicographically.
- Deterministic record iteration: file order (line order).
- Strict schema validation aligned to Phase 5 store contract:
  required keys: memory_id, type, source, created_at_utc, hash
- refs must be list[dict] if present.
- tags normalized to sorted unique lowercase strings.
- record_hash uses record["hash"] when present and valid; otherwise computed deterministically
  over canonical fields excluding "hash".
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Iterator, List, Optional, Sequence

from adam_os.memory.canonical import canonical_dumps, hash_record_fields


class JsonlReaderError(ValueError):
    """Raised when JSONL store reading or schema validation fails."""


_REQUIRED_KEYS = ("memory_id", "type", "source", "created_at_utc", "hash")


def _require_str(name: str, value: Any) -> str:
    if not isinstance(value, str):
        raise JsonlReaderError(f"{name} must be str")
    if value.strip() == "":
        raise JsonlReaderError(f"{name} must be non-empty")
    return value


def _normalize_tags(tags: Any) -> List[str]:
    if tags is None:
        return []
    if not isinstance(tags, list):
        raise JsonlReaderError("tags must be list[str]")
    out: List[str] = []
    for i, t in enumerate(tags):
        if not isinstance(t, str):
            raise JsonlReaderError(f"tags[{i}] must be str")
        s = t.strip().lower()
        if s == "":
            continue
        out.append(s)
    # deterministic: unique + sorted
    return sorted(set(out))


def _validate_refs(refs: Any) -> List[Dict[str, Any]]:
    if refs is None:
        return []
    if not isinstance(refs, list):
        raise JsonlReaderError("refs must be list[dict]")
    out: List[Dict[str, Any]] = []
    for i, r in enumerate(refs):
        if not isinstance(r, dict):
            raise JsonlReaderError(f"refs[{i}] must be dict")
        out.append(r)
    return out


def _record_hash(record: Dict[str, Any]) -> str:
    # Prefer Phase 5 store hash field if present and valid.
    h = record.get("hash")
    if isinstance(h, str) and h.strip() != "":
        return h

    # Otherwise compute deterministically excluding any 'hash' field.
    if "hash" in record:
        tmp = dict(record)
        tmp.pop("hash", None)
    else:
        tmp = record
    # Ensure canonicalization is deterministic before hashing.
    _ = canonical_dumps(tmp)
    return hash_record_fields(tmp)


@dataclass(frozen=True)
class MemoryCandidate:
    memory_id: str
    record_hash: str
    store_path: str
    created_at_utc: str
    record_type: str
    source: str
    text: str
    tags: List[str]
    refs: List[Dict[str, Any]]
    line_no: int


def iter_jsonl_candidates(store_paths: Sequence[str]) -> Iterator[MemoryCandidate]:
    """Yield MemoryCandidate items deterministically from JSONL stores.

    Determinism:
    - store_paths are normalized to strings and sorted lexicographically
    - each file is read line-by-line in file order
    """
    if not isinstance(store_paths, (list, tuple)):
        raise JsonlReaderError("store_paths must be a sequence of strings")
    if len(store_paths) == 0:
        raise JsonlReaderError("store_paths must be non-empty")

    normalized_paths = sorted([str(p) for p in store_paths])

    for sp in normalized_paths:
        p = Path(sp)
        if not p.exists():
            raise JsonlReaderError(f"store path does not exist: {sp}")
        if not p.is_file():
            raise JsonlReaderError(f"store path is not a file: {sp}")

        with p.open("r", encoding="utf-8") as f:
            for idx, raw in enumerate(f, start=1):
                s = raw.rstrip("\n")
                if s.strip() == "":
                    continue

                try:
                    obj = json.loads(s)
                except json.JSONDecodeError as e:
                    raise JsonlReaderError(f"invalid JSON on line {idx} in {sp}: {e}") from None

                if not isinstance(obj, dict):
                    raise JsonlReaderError(f"non-object JSON on line {idx} in {sp}")

                for k in _REQUIRED_KEYS:
                    if k not in obj:
                        raise JsonlReaderError(f"record missing required key '{k}' on line {idx} in {sp}")

                memory_id = _require_str("memory_id", obj.get("memory_id"))
                record_type = _require_str("type", obj.get("type"))
                source = _require_str("source", obj.get("source"))
                created_at_utc = _require_str("created_at_utc", obj.get("created_at_utc"))

                # text is expected in Phase 5 records, but enforce here to keep controller simpler.
                text_val = obj.get("text")
                if not isinstance(text_val, str):
                    raise JsonlReaderError(f"text must be str on line {idx} in {sp}")
                text = text_val.strip()

                tags = _normalize_tags(obj.get("tags"))
                refs = _validate_refs(obj.get("refs"))

                rh = _record_hash(obj)

                yield MemoryCandidate(
                    memory_id=memory_id,
                    record_hash=rh,
                    store_path=sp,
                    created_at_utc=created_at_utc,
                    record_type=record_type,
                    source=source,
                    text=text,
                    tags=tags,
                    refs=refs,
                    line_no=idx,
                )


__all__ = [
    "JsonlReaderError",
    "MemoryCandidate",
    "iter_jsonl_candidates",
]
