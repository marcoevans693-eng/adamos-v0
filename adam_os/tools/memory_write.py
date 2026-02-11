# Procedure: Phase 5 tool - memory.write (append-only store write; no ledger writes here)
"""
Memory write tool (Phase 5)

This tool performs an append-only write to a JSONL memory store using the Phase 5
utilities. It does NOT write to the run ledger; the dispatcher owns receipts.

Tool name: "memory.write"

Expected tool_input:
{
  "store_path": "<path to jsonl store>",
  "record": {
      "type": "<string>",
      "source": "<string>",
      "tags": ["..."] (optional),
      "text": "<string>",
      "refs": {...} (optional),
      "created_at_utc": "<iso8601>" (optional),
      "memory_id": "<string>" (optional)
  }
}

Returns:
{
  "memory_id": "<id>",
  "record_hash": "<sha256-ish hash from Phase 5 utils>",
  "store_path": "<store_path>"
}
"""

from __future__ import annotations

from typing import Any, Dict

from adam_os.memory.records import build_memory_record
from adam_os.memory.store import append_record


TOOL_NAME = "memory.write"


def memory_write(tool_input: Dict[str, Any]) -> Dict[str, Any]:
    """
    Append a deterministic memory record to a JSONL store and return ids/hashes.

    NOTE: This function must remain side-effect limited to the store append only.
          No ledger writes. No printing. No hidden I/O beyond append_record().
    """
    if not isinstance(tool_input, dict):
        raise TypeError("tool_input must be dict")

    store_path = tool_input.get("store_path")
    if not isinstance(store_path, str) or not store_path.strip():
        raise ValueError("tool_input.store_path must be a non-empty string")

    rec = tool_input.get("record")
    if not isinstance(rec, dict):
        raise ValueError("tool_input.record must be a dict")

    record = build_memory_record(
        record_type=rec.get("type"),
        source=rec.get("source"),
        tags=rec.get("tags"),
        text=rec.get("text"),
        refs=rec.get("refs"),
        created_at_utc=rec.get("created_at_utc"),
        memory_id=rec.get("memory_id"),
    )

    append_record(store_path, record)

    return {
        "memory_id": record["memory_id"],
        "record_hash": record["hash"],
        "store_path": store_path,
    }
