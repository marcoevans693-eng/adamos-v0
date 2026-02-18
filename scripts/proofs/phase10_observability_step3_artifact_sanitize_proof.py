# Procedure: Proof — Phase10 Step3 Part4 (artifact.sanitize emits engineering activity events)
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List

from adam_os.tools.artifact_sanitize import artifact_sanitize
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


def main() -> None:
    before = _read_jsonl(ACT_LOG)
    before_n = len(before)

    artifact_root = Path(".adam_os") / "artifacts"
    raw_dir = artifact_root / "raw"
    raw_dir.mkdir(parents=True, exist_ok=True)

    # IMPORTANT: append-only system => IDs must be unique per proof run
    run_tag = str(before_n)
    raw_id = f"phase10_sanitize_raw_{run_tag}"
    sanitized_id = f"{raw_id}--sanitized"

    raw_path = raw_dir / f"{raw_id}.txt"
    raw_path.write_text("hello world.\nWhat is this?\nProbably fine.\n", encoding="utf-8")

    # 1) Success (fresh IDs => cannot be idempotent)
    r1 = artifact_sanitize(
        {
            "created_at_utc": "2026-02-17T12:00:00Z",
            "raw_artifact_id": raw_id,
            "sanitized_artifact_id": sanitized_id,
            "media_type": "application/jsonl",
        }
    )
    assert r1["kind"] == "SANITIZED"
    assert r1["artifact_id"] == sanitized_id

    mid = _read_jsonl(ACT_LOG)
    assert len(mid) == before_n + 1, "expected exactly 1 new engineering event after success call"

    last_mid = _last_tool_event(mid, "artifact.sanitize")
    assert last_mid["event_type"] == "tool_execute"
    assert last_mid["tool_name"] == "artifact.sanitize"
    assert last_mid["status"] == "success"

    # 2) Idempotent (same IDs again)
    r2 = artifact_sanitize(
        {
            "created_at_utc": "2026-02-17T12:00:01Z",
            "raw_artifact_id": raw_id,
            "sanitized_artifact_id": sanitized_id,
            "media_type": "application/jsonl",
        }
    )
    assert r2["kind"] == "SANITIZED"
    assert r2["artifact_id"] == r1["artifact_id"]

    mid2 = _read_jsonl(ACT_LOG)
    assert len(mid2) == before_n + 2, "expected exactly 1 new engineering event after idempotent call"

    last_mid2 = _last_tool_event(mid2, "artifact.sanitize")
    assert last_mid2["event_type"] == "tool_execute"
    assert last_mid2["tool_name"] == "artifact.sanitize"
    assert last_mid2["status"] == "idempotent"

    # 3) Error (missing raw artifact)
    try:
        artifact_sanitize(
            {
                "created_at_utc": "2026-02-17T12:00:02Z",
                "raw_artifact_id": f"{raw_id}_missing",
            }
        )
        raise AssertionError("expected FileNotFoundError, but call succeeded")
    except FileNotFoundError:
        pass

    after = _read_jsonl(ACT_LOG)
    assert len(after) == before_n + 3, "expected exactly 1 additional engineering event after error case"

    last_after = _last_tool_event(after, "artifact.sanitize")
    assert last_after["event_type"] == "tool_execute"
    assert last_after["tool_name"] == "artifact.sanitize"
    assert last_after["status"] == "error"

    print(
        json.dumps(
            {
                "ok": True,
                "tool": "artifact.sanitize",
                "new_events_added": 3,
                "statuses": ["success", "idempotent", "error"],
            },
            indent=2,
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
