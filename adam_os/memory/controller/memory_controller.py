"""
Phase 6 Step 4 — Memory Controller (Deterministic Read + Score + Bounded Assembly)

This module is Phase 6 scope ONLY:
- retrieval + scoring + bounded assembly
- no semantic promotion
- no autonomy
- no probabilistic logic
- no store mutation
- no ledger writes
- no system time reads (recency only if now_utc provided by caller)

Token estimation:
- Deterministic approximation (char-based). It is NOT model-accurate.
- Purpose: enforce an explicit, repeatable budget guardrail.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict, List, Optional, Sequence, Tuple

from adam_os.memory.scoring.deterministic_scorer import DeterministicScorer, ScoredRecord


def _estimate_tokens(text: str) -> int:
    """
    Deterministic token estimate.

    Rule:
      approx_tokens = ceil(len(text) / 4)
    Implemented using integer math:
      (n + 3) // 4

    Adds a small constant overhead for formatting stability.
    """
    if not text:
        return 0
    n = len(text)
    return ((n + 3) // 4)


def _render_record_for_context(record: Dict[str, Any]) -> str:
    """
    Deterministic record rendering for context package.
    This MUST remain stable across runs.

    Record fields are read-only and best-effort:
      - record_id
      - ts_utc / created_at_utc / timestamp_utc
      - tags
      - text/content
    """
    record_id = str(record.get("record_id") or record.get("id") or "")
    ts = record.get("ts_utc") or record.get("created_at_utc") or record.get("timestamp_utc") or ""
    tags = record.get("tags") or []
    if isinstance(tags, (list, tuple, set)):
        tag_list = [str(t).strip() for t in tags if str(t).strip()]
    else:
        tag_list = [str(tags).strip()] if str(tags).strip() else []

    text = record.get("text")
    if text is None:
        text = record.get("content")
    if text is None:
        text = ""
    text = str(text)

    # stable formatting
    tag_str = ", ".join(tag_list)

    lines = [
        f"record_id: {record_id}",
        f"ts_utc: {ts}",
        f"tags: {tag_str}",
        "text:",
        text,
    ]
    return "\n".join(lines).strip()


@dataclass(frozen=True)
class MemoryReadRequest:
    query: str
    records: Sequence[Dict[str, Any]]

    # hard limits
    token_budget: int
    max_items: int

    # optional signals
    query_tags: Optional[Sequence[str]] = None
    now_utc: Optional[datetime] = None


@dataclass(frozen=True)
class MemoryReadResult:
    items: List[ScoredRecord]
    context_text: str
    token_budget: int
    tokens_used: int
    truncated: bool


class MemoryController:
    """
    Deterministic Memory Controller (Phase 6).

    Input:
      - in-memory records provided by caller (Phase 6 does not mandate store access here)
    Output:
      - scored items (ordered)
      - bounded context_text assembled deterministically

    NOTE:
      Wiring to an on-disk store reader happens at a higher layer.
      This controller is pure compute over provided records.
    """

    def __init__(self, scorer: Optional[DeterministicScorer] = None) -> None:
        self._scorer = scorer or DeterministicScorer()

    def read(self, req: MemoryReadRequest) -> MemoryReadResult:
        if not isinstance(req.token_budget, int) or req.token_budget <= 0:
            raise ValueError("token_budget must be a positive int")
        if not isinstance(req.max_items, int) or req.max_items <= 0:
            raise ValueError("max_items must be a positive int")

        scored = self._scorer.score(
            req.query,
            req.records,
            query_tags=req.query_tags,
            now_utc=req.now_utc,
        )

        # Deterministic assembly within budget + max_items
        header = f"MEMORY_CONTEXT\nquery: {req.query}\n"
        header_tokens = _estimate_tokens(header)

        tokens_used = header_tokens
        parts: List[str] = [header.rstrip()]
        items_out: List[ScoredRecord] = []

        truncated = False

        for s in scored:
            if len(items_out) >= req.max_items:
                truncated = True
                break

            rendered = _render_record_for_context(s.record)
            # add stable separator
            block = "\n---\n" + rendered
            block_tokens = _estimate_tokens(block)

            if tokens_used + block_tokens > req.token_budget:
                truncated = True
                break

            parts.append(block)
            items_out.append(s)
            tokens_used += block_tokens

        context_text = "\n".join(parts).strip() + "\n"
        return MemoryReadResult(
            items=items_out,
            context_text=context_text,
            token_budget=req.token_budget,
            tokens_used=tokens_used,
            truncated=truncated,
        )
