"""
Phase 6 Step 5 — memory.read API (Deterministic)

Orchestrates:
  store_paths -> JSONL candidates -> controller scoring -> bounded context

Hard rules:
- deterministic
- no ledger writes
- no store mutation
- no system time reads (recency only if now_utc provided)
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict, List, Optional, Sequence

from adam_os.memory.controller.memory_controller import MemoryController, MemoryReadRequest, MemoryReadResult
from adam_os.memory.readers.jsonl_reader import iter_jsonl_candidates


def _candidate_to_record(c: Any) -> Dict[str, Any]:
    """
    Map MemoryCandidate -> controller record shape deterministically.

    Controller expects (best-effort):
      - record_id
      - ts_utc / created_at_utc / timestamp_utc
      - tags
      - text/content
    """
    return {
        "record_id": c.memory_id,
        "ts_utc": c.created_at_utc,
        "tags": list(c.tags),
        "text": c.text,
        # keep provenance fields for future use; controller ignores unknown keys
        "source": c.source,
        "type": c.record_type,
        "record_hash": c.record_hash,
        "store_path": c.store_path,
        "line_no": c.line_no,
        "refs": list(c.refs),
    }


def memory_read(
    *,
    store_paths: Sequence[str],
    query: str,
    token_budget: int,
    max_items: int,
    query_tags: Optional[Sequence[str]] = None,
    now_utc: Optional[datetime] = None,
    controller: Optional[MemoryController] = None,
) -> MemoryReadResult:
    """
    Deterministic memory read.

    Inputs:
      - store_paths: JSONL files (Phase 5/6 store)
      - query: text query
      - token_budget, max_items: explicit hard limits
      - query_tags: optional explicit tag set
      - now_utc: optional explicit clock (never read system time)
      - controller: optional injected controller (for testing)

    Output:
      - MemoryReadResult with bounded context_text and scored items
    """
    mc = controller or MemoryController()

    records: List[Dict[str, Any]] = []
    for cand in iter_jsonl_candidates(store_paths):
        records.append(_candidate_to_record(cand))

    req = MemoryReadRequest(
        query=query,
        records=records,
        token_budget=token_budget,
        max_items=max_items,
        query_tags=query_tags,
        now_utc=now_utc,
    )
    return mc.read(req)
