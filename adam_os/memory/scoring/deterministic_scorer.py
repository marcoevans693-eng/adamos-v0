"""
Phase 6 Step 3 — Deterministic Scorer

Hard rules:
- No randomness
- No system time reads (recency only if now_utc is provided)
- No I/O, no ledger writes, no store mutation
- Deterministic ordering with explicit tie-breaks
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import re
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple


_TOKEN_RE = re.compile(r"[a-z0-9]+", re.IGNORECASE)


def _normalize_tokens(text: str) -> Tuple[str, ...]:
    """
    Deterministic normalization:
    - lowercase
    - extract [a-z0-9]+ tokens
    - return sorted tuple for stable downstream behavior
    """
    if not text:
        return tuple()
    tokens = _TOKEN_RE.findall(text.lower())
    if not tokens:
        return tuple()
    # sorted() ensures stable output independent of regex scan quirks
    return tuple(sorted(tokens))


def _parse_ts_utc(value: Any) -> Optional[int]:
    """
    Convert a record timestamp to epoch seconds (UTC) deterministically.
    Accepts:
      - int/float epoch seconds
      - ISO8601 string (e.g. '2026-02-10T12:34:56Z' or with offset)
      - datetime
    Returns:
      - int epoch seconds, or None if missing/unparseable
    """
    if value is None:
        return None

    if isinstance(value, int):
        return value
    if isinstance(value, float):
        # floor for determinism
        return int(value)

    if isinstance(value, datetime):
        dt = value
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return int(dt.timestamp())

    if isinstance(value, str):
        s = value.strip()
        if not s:
            return None
        # Common case: trailing Z
        if s.endswith("Z"):
            s = s[:-1] + "+00:00"
        try:
            dt = datetime.fromisoformat(s)
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            return int(dt.timestamp())
        except Exception:
            return None

    return None


def _recency_points(now_utc_epoch: int, record_epoch: int) -> int:
    """
    Deterministic recency points using integer bucketization (no floats).
    Newer => more points. Old => fewer points.

    Buckets (age):
      0-1 days   => 20
      2-7 days   => 12
      8-30 days  => 6
      31-180     => 2
      181+       => 0
    """
    age_sec = now_utc_epoch - record_epoch
    if age_sec < 0:
        # Future timestamps get treated as newest (still deterministic)
        return 20
    age_days = age_sec // 86400

    if age_days <= 1:
        return 20
    if age_days <= 7:
        return 12
    if age_days <= 30:
        return 6
    if age_days <= 180:
        return 2
    return 0


@dataclass(frozen=True)
class ScoredRecord:
    record: Dict[str, Any]
    score: int
    term_overlap: int
    tag_overlap: int
    recency: int
    sort_key: Tuple[int, int, str, int]
    """
    sort_key is a fully deterministic tuple used for ordering:
      (-score, -record_epoch_or_-inf, record_id, original_index)
    """


class DeterministicScorer:
    """
    Deterministic scoring over a batch of memory records.

    Expected record shape (minimum):
      - record_id: str  (if absent, we fall back to '' but tie-break stability is better with IDs)
      - text: str       (if absent, tries 'content' then '')
      - tags: list[str] or set[str] or tuple[str] (optional)
      - ts_utc / created_at_utc / timestamp_utc: int|float|str|datetime (optional)

    Query inputs:
      - query: str
      - query_tags: optional explicit tag set
      - now_utc: optional datetime (must be provided by caller; never read system time)
    """

    # Integer weights (stable, obvious)
    W_TERM = 100
    W_TAG = 30
    W_RECENCY = 1

    def score(
        self,
        query: str,
        records: Sequence[Dict[str, Any]],
        *,
        query_tags: Optional[Iterable[str]] = None,
        now_utc: Optional[datetime] = None,
    ) -> List[ScoredRecord]:
        q_tokens = _normalize_tokens(query)

        q_tag_set = set()
        if query_tags:
            for t in query_tags:
                if t is None:
                    continue
                s = str(t).strip().lower()
                if s:
                    q_tag_set.add(s)

        now_epoch: Optional[int] = None
        if now_utc is not None:
            dt = now_utc
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            now_epoch = int(dt.timestamp())

        scored: List[ScoredRecord] = []

        for idx, r in enumerate(records):
            record_id = str(r.get("record_id") or r.get("id") or "")

            text = r.get("text")
            if text is None:
                text = r.get("content")
            if text is None:
                text = ""
            text = str(text)

            r_tokens = _normalize_tokens(text)

            # overlap is based on multiset? We choose set overlap for stability + simplicity.
            # Convert tuples to sets deterministically.
            term_overlap = len(set(q_tokens).intersection(set(r_tokens)))

            # Tag overlap (optional)
            tag_overlap = 0
            tags_val = r.get("tags")
            if tags_val is not None:
                if isinstance(tags_val, (list, tuple, set)):
                    r_tag_set = {str(t).strip().lower() for t in tags_val if str(t).strip()}
                else:
                    # single string case
                    r_tag_set = {str(tags_val).strip().lower()} if str(tags_val).strip() else set()
                if q_tag_set and r_tag_set:
                    tag_overlap = len(q_tag_set.intersection(r_tag_set))

            # Recency points only if caller provided now_utc and record timestamp exists
            recency = 0
            record_epoch = None
            if now_epoch is not None:
                record_epoch = _parse_ts_utc(
                    r.get("ts_utc") or r.get("created_at_utc") or r.get("timestamp_utc")
                )
                if record_epoch is not None:
                    recency = _recency_points(now_epoch, record_epoch)

            score_val = (term_overlap * self.W_TERM) + (tag_overlap * self.W_TAG) + (recency * self.W_RECENCY)

            # Stable tie-break:
            # 1) higher score first => -score
            # 2) newer timestamp first (only if known) => -record_epoch; unknown treated as very old
            # 3) record_id lexicographic
            # 4) original index for absolute stability
            ts_component = record_epoch if record_epoch is not None else -1
            sort_key = (-score_val, -ts_component, record_id, idx)

            scored.append(
                ScoredRecord(
                    record=r,
                    score=score_val,
                    term_overlap=term_overlap,
                    tag_overlap=tag_overlap,
                    recency=recency,
                    sort_key=sort_key,
                )
            )

        scored.sort(key=lambda x: x.sort_key)
        return scored
