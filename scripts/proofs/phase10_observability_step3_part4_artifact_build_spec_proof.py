# Procedure: Proof — Phase10 Step3 Part4 (artifact.build_spec emits engineering activity events)
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List

from adam_os.tools.artifact_build_spec import artifact_build_spec

ACT_LOG = Path(".adam_os/engineering/activity_log.jsonl")


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


def _tail_tool_events(events: List[Dict[str, Any]], tool_name: str) -> List[Dict[str, Any]]:
    return [e for e in events if e.get("event_type") == "tool_execute" and e.get("tool_name") == tool_name]


def main() -> None:
    before = _read_jsonl(ACT_LOG)
    before_n = len(before)

    # Use an existing bundle artifact if present, else fail loudly with a clear message.
    bundles_dir = Path(".adam_os/artifacts/bundles")
    bundle_files = sorted(bundles_dir.glob("*.json"))
    if not bundle_files:
        raise RuntimeError("no bundle manifests found under .adam_os/artifacts/bundles/ (Phase 7 output required)")

    bundle_id = bundle_files[0].stem

    # 1) Success OR idempotent (depending on whether spec already exists)
    r1 = artifact_build_spec(
        {
            "created_at_utc": "2026-02-17T10:00:00Z",
            "bundle_artifact_id": bundle_id,
            "provider": "openai",
            "model": "gpt-4o-mini",
            "temperature": 0,
            "max_tokens": 64,
        }
    )
    assert r1["kind"] == "BUILD_SPEC"
    assert r1["artifact_id"].endswith("--build_spec")

    mid = _read_jsonl(ACT_LOG)
    assert len(mid) == before_n + 1, "expected exactly 1 new engineering event after first call"

    tool_events_mid = _tail_tool_events(mid[before_n:], "artifact.build_spec")
    assert len(tool_events_mid) == 1, "expected the new event to be for artifact.build_spec"
    assert tool_events_mid[0]["status"] in ("success", "idempotent")
    assert tool_events_mid[0].get("artifact_id") == r1["artifact_id"]

    # 2) Second call must be idempotent (spec exists + registry already contains BUILD_SPEC)
    r2 = artifact_build_spec(
        {
            "created_at_utc": "2026-02-17T10:00:01Z",
            "bundle_artifact_id": bundle_id,
            "provider": "openai",
            "model": "gpt-4o-mini",
            "temperature": 0,
            "max_tokens": 64,
        }
    )
    assert r2["kind"] == "BUILD_SPEC"
    assert r2["artifact_id"] == r1["artifact_id"]

    after2 = _read_jsonl(ACT_LOG)
    assert len(after2) == before_n + 2, "expected exactly 1 additional engineering event after second call"

    tool_events_after2 = _tail_tool_events(after2[before_n:], "artifact.build_spec")
    assert len(tool_events_after2) == 2
    assert tool_events_after2[1]["status"] == "idempotent"
    assert tool_events_after2[1].get("artifact_id") == r1["artifact_id"]

    # 3) Error case must log status=error
    try:
        artifact_build_spec(
            {
                "created_at_utc": "2026-02-17T10:00:02Z",
                "bundle_artifact_id": "does-not-exist-bundle",
                "provider": "openai",
                "model": "gpt-4o-mini",
            }
        )
        raise AssertionError("expected error, but call succeeded")
    except Exception:
        pass

    after3 = _read_jsonl(ACT_LOG)
    assert len(after3) == before_n + 3, "expected exactly 1 additional engineering event after error case"

    tool_events_after3 = _tail_tool_events(after3[before_n:], "artifact.build_spec")
    assert len(tool_events_after3) == 3
    assert tool_events_after3[2]["status"] == "error"
    assert tool_events_after3[2].get("exception_type") is not None
    assert tool_events_after3[2].get("exception_message") is not None

    print(
        json.dumps(
            {
                "ok": True,
                "tool": "artifact.build_spec",
                "bundle_id_used": bundle_id,
                "new_events_added": 3,
                "statuses": [tool_events_after3[0]["status"], tool_events_after3[1]["status"], tool_events_after3[2]["status"]],
            },
            indent=2,
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
