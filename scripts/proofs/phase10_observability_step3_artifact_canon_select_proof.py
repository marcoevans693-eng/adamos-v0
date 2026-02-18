# Procedure: Proof — Phase10 Step3 Part4 (artifact.canon_select emits engineering activity events)
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List
from uuid import uuid4

from adam_os.memory.canonical import canonical_dumps
from adam_os.tools.artifact_canon_select import artifact_canon_select
from adam_os.tools.engineering_log_append import DEFAULT_ACTIVITY_LOG_PATH


ACT_LOG = Path(DEFAULT_ACTIVITY_LOG_PATH)


def _read_jsonl(path: Path) -> List[Dict[str, Any]]:
    if not path.exists():
        return []
    out: List[Dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            out.append(json.loads(line))
    return out


def _last_tool_event(events: List[Dict[str, Any]], tool_name: str) -> Dict[str, Any]:
    for e in reversed(events):
        if e.get("event_type") == "tool_execute" and e.get("tool_name") == tool_name:
            return e
    raise AssertionError("no tool_execute event found for tool: " + tool_name)


def _write_sanitized_jsonl(path: Path) -> None:
    lines = [
        {"type": "SOURCE-BASED", "text": "alpha"},
        {"type": "SOURCE-BASED", "text": "beta"},
        {"type": "NOTE", "text": "gamma"},
    ]
    text = "".join(canonical_dumps(obj) + "\n" for obj in lines)
    path.write_text(text, encoding="utf-8")


def main() -> None:
    before = _read_jsonl(ACT_LOG)
    before_n = len(before)

    artifact_root = Path(".adam_os") / "artifacts"
    sanitized_dir = artifact_root / "sanitized"
    sanitized_dir.mkdir(parents=True, exist_ok=True)

    # IMPORTANT: append-only system => IDs must be unique per proof run
    run_tag = uuid4().hex
    sanitized_id = f"phase10_canon_select_sanitized_{run_tag}"
    canon_id = f"phase10_canon_select_canon_{run_tag}"

    sanitized_path = sanitized_dir / f"{sanitized_id}.jsonl"
    _write_sanitized_jsonl(sanitized_path)

    # 1) Success (fresh IDs => cannot be idempotent)
    r1 = artifact_canon_select(
        {
            "created_at_utc": "2026-02-17T12:10:00Z",
            "sanitized_artifact_id": sanitized_id,
            "canon_artifact_id": canon_id,
            "media_type": "application/jsonl",
        }
    )
    assert r1["kind"] == "BUNDLE_MANIFEST"
    assert r1["artifact_id"] == canon_id

    mid = _read_jsonl(ACT_LOG)
    assert len(mid) == before_n + 1, "expected exactly 1 new engineering event after success call"

    last_mid = _last_tool_event(mid, "artifact.canon_select")
    assert last_mid["event_type"] == "tool_execute"
    assert last_mid["tool_name"] == "artifact.canon_select"
    assert last_mid["status"] == "success"

    # 2) Idempotent (same IDs again)
    r2 = artifact_canon_select(
        {
            "created_at_utc": "2026-02-17T12:10:01Z",
            "sanitized_artifact_id": sanitized_id,
            "canon_artifact_id": canon_id,
            "media_type": "application/jsonl",
        }
    )
    assert r2["kind"] == "BUNDLE_MANIFEST"
    assert r2["artifact_id"] == r1["artifact_id"]

    mid2 = _read_jsonl(ACT_LOG)
    assert len(mid2) == before_n + 2, "expected exactly 1 new engineering event after idempotent call"

    last_mid2 = _last_tool_event(mid2, "artifact.canon_select")
    assert last_mid2["event_type"] == "tool_execute"
    assert last_mid2["tool_name"] == "artifact.canon_select"
    assert last_mid2["status"] == "idempotent"

    # 3) Error (missing sanitized artifact)
    try:
        artifact_canon_select(
            {
                "created_at_utc": "2026-02-17T12:10:02Z",
                "sanitized_artifact_id": f"{sanitized_id}_missing",
            }
        )
        raise AssertionError("expected FileNotFoundError, but call succeeded")
    except FileNotFoundError:
        pass

    after = _read_jsonl(ACT_LOG)
    assert len(after) == before_n + 3, "expected exactly 1 additional engineering event after error case"

    last_after = _last_tool_event(after, "artifact.canon_select")
    assert last_after["event_type"] == "tool_execute"
    assert last_after["tool_name"] == "artifact.canon_select"
    assert last_after["status"] == "error"

    print(
        json.dumps(
            {
                "ok": True,
                "tool": "artifact.canon_select",
                "new_events_added": 3,
                "statuses": ["success", "idempotent", "error"],
            },
            indent=2,
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
