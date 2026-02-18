# Procedure: Proof — Phase10 Step3 Part4 (artifact.work_order_emit emits engineering activity events)
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List
from uuid import uuid4

from adam_os.memory.canonical import canonical_dumps
from adam_os.tools.artifact_work_order_emit import artifact_work_order_emit
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


def _write_json(path: Path, obj: Dict[str, Any]) -> None:
    text = canonical_dumps(obj) + "\n"
    path.write_text(text, encoding="utf-8")


def main() -> None:
    before = _read_jsonl(ACT_LOG)
    before_n = len(before)

    artifact_root = Path(".adam_os") / "artifacts"
    specs_dir = artifact_root / "specs"
    work_orders_dir = artifact_root / "work_orders"
    specs_dir.mkdir(parents=True, exist_ok=True)
    work_orders_dir.mkdir(parents=True, exist_ok=True)

    # IMPORTANT: append-only system => IDs must be unique per proof run
    run_tag = uuid4().hex
    spec_id = f"phase10_work_order_spec_{run_tag}"
    work_order_id = f"phase10_work_order_emit_{run_tag}"

    spec_path = specs_dir / f"{spec_id}.json"
    _write_json(
        spec_path,
        {
            "bundle": {"bundle_hash": "a" * 64},
            "audit": {"prompt_hash": "b" * 64},
            "spec": {"OPEN_QUESTIONS": [], "foo": "bar"},
        },
    )

    # 1) Success (fresh IDs => cannot be idempotent)
    r1 = artifact_work_order_emit(
        {
            "created_at_utc": "2026-02-17T12:30:00Z",
            "build_spec_artifact_id": spec_id,
            "work_order_artifact_id": work_order_id,
        }
    )
    assert r1["kind"] == "WORK_ORDER"
    assert r1["artifact_id"] == work_order_id
    assert r1["build_spec_artifact_id"] == spec_id
    assert r1["work_order_hash"]

    mid = _read_jsonl(ACT_LOG)
    assert len(mid) == before_n + 1, "expected exactly 1 new engineering event after success call"

    last_mid = _last_tool_event(mid, "artifact.work_order_emit")
    assert last_mid["event_type"] == "tool_execute"
    assert last_mid["tool_name"] == "artifact.work_order_emit"
    assert last_mid["status"] == "success"

    # 2) Idempotent (same IDs again)
    r2 = artifact_work_order_emit(
        {
            "created_at_utc": "2026-02-17T12:30:01Z",
            "build_spec_artifact_id": spec_id,
            "work_order_artifact_id": work_order_id,
        }
    )
    assert r2["kind"] == "WORK_ORDER"
    assert r2["artifact_id"] == r1["artifact_id"]

    mid2 = _read_jsonl(ACT_LOG)
    assert len(mid2) == before_n + 2, "expected exactly 1 new engineering event after idempotent call"

    last_mid2 = _last_tool_event(mid2, "artifact.work_order_emit")
    assert last_mid2["event_type"] == "tool_execute"
    assert last_mid2["tool_name"] == "artifact.work_order_emit"
    assert last_mid2["status"] == "idempotent"

    # 3) Error (missing build spec)
    try:
        artifact_work_order_emit(
            {
                "created_at_utc": "2026-02-17T12:30:02Z",
                "build_spec_artifact_id": f"{spec_id}_missing",
                "work_order_artifact_id": f"{work_order_id}_missing",
            }
        )
        raise AssertionError("expected FileNotFoundError, but call succeeded")
    except FileNotFoundError:
        pass

    after = _read_jsonl(ACT_LOG)
    assert len(after) == before_n + 3, "expected exactly 1 additional engineering event after error case"

    last_after = _last_tool_event(after, "artifact.work_order_emit")
    assert last_after["event_type"] == "tool_execute"
    assert last_after["tool_name"] == "artifact.work_order_emit"
    assert last_after["status"] == "error"

    print(
        json.dumps(
            {
                "ok": True,
                "tool": "artifact.work_order_emit",
                "new_events_added": 3,
                "statuses": ["success", "idempotent", "error"],
            },
            indent=2,
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
