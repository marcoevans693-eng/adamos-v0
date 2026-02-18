# Procedure: Proof — Phase10 Step3 Part4 (artifact.bundle_manifest emits engineering activity events)
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List
from uuid import uuid4

from adam_os.artifacts.registry import ArtifactRegistry
from adam_os.memory.canonical import canonical_dumps
from adam_os.tools.artifact_bundle_manifest import artifact_bundle_manifest
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


def _write_jsonl(path: Path, obj: Dict[str, Any]) -> None:
    text = canonical_dumps(obj) + "\n"
    path.write_text(text, encoding="utf-8")


def main() -> None:
    before = _read_jsonl(ACT_LOG)
    before_n = len(before)

    artifact_root = Path(".adam_os") / "artifacts"
    raw_dir = artifact_root / "raw"
    sanitized_dir = artifact_root / "sanitized"
    bundles_dir = artifact_root / "bundles"
    raw_dir.mkdir(parents=True, exist_ok=True)
    sanitized_dir.mkdir(parents=True, exist_ok=True)
    bundles_dir.mkdir(parents=True, exist_ok=True)

    # IMPORTANT: append-only system => IDs must be unique per proof run
    run_tag = uuid4().hex
    raw_id = f"phase10_bundle_manifest_raw_{run_tag}"
    san_id = f"phase10_bundle_manifest_sanitized_{run_tag}"
    canon_id = f"phase10_bundle_manifest_canon_{run_tag}"
    bundle_id = f"phase10_bundle_manifest_bundle_{run_tag}"

    raw_path = raw_dir / f"{raw_id}.txt"
    raw_path.write_text("raw\n", encoding="utf-8")

    sanitized_path = sanitized_dir / f"{san_id}.jsonl"
    _write_jsonl(sanitized_path, {"type": "SOURCE-BASED", "text": "alpha"})

    canon_path = bundles_dir / f"{canon_id}.jsonl"
    _write_jsonl(canon_path, {"type": "SOURCE-BASED", "text": "alpha"})

    reg = ArtifactRegistry(artifact_root=artifact_root)

    reg.append_from_file(
        artifact_id=raw_id,
        kind="RAW",
        created_at_utc="2026-02-17T12:20:00Z",
        file_path=raw_path,
        media_type="text/plain",
        parent_artifact_ids=[],
        notes="proof.raw",
        tags=["proof", "raw"],
    )
    reg.append_from_file(
        artifact_id=san_id,
        kind="SANITIZED",
        created_at_utc="2026-02-17T12:20:01Z",
        file_path=sanitized_path,
        media_type="application/jsonl",
        parent_artifact_ids=[raw_id],
        notes="proof.sanitized",
        tags=["proof", "sanitized"],
    )
    reg.append_from_file(
        artifact_id=canon_id,
        kind="BUNDLE_MANIFEST",
        created_at_utc="2026-02-17T12:20:02Z",
        file_path=canon_path,
        media_type="application/jsonl",
        parent_artifact_ids=[san_id],
        notes="proof.canon",
        tags=["proof", "canon"],
    )

    # 1) Success (fresh IDs => cannot be idempotent)
    r1 = artifact_bundle_manifest(
        {
            "created_at_utc": "2026-02-17T12:20:03Z",
            "canon_artifact_id": canon_id,
            "bundle_artifact_id": bundle_id,
            "media_type": "application/json",
        }
    )
    assert r1["kind"] == "BUNDLE_MANIFEST"
    assert r1["artifact_id"] == bundle_id
    assert r1["member_count"] == 3

    mid = _read_jsonl(ACT_LOG)
    assert len(mid) == before_n + 1, "expected exactly 1 new engineering event after success call"

    last_mid = _last_tool_event(mid, "artifact.bundle_manifest")
    assert last_mid["event_type"] == "tool_execute"
    assert last_mid["tool_name"] == "artifact.bundle_manifest"
    assert last_mid["status"] == "success"

    # 2) Idempotent (same IDs again)
    r2 = artifact_bundle_manifest(
        {
            "created_at_utc": "2026-02-17T12:20:04Z",
            "canon_artifact_id": canon_id,
            "bundle_artifact_id": bundle_id,
            "media_type": "application/json",
        }
    )
    assert r2["kind"] == "BUNDLE_MANIFEST"
    assert r2["artifact_id"] == r1["artifact_id"]

    mid2 = _read_jsonl(ACT_LOG)
    assert len(mid2) == before_n + 2, "expected exactly 1 new engineering event after idempotent call"

    last_mid2 = _last_tool_event(mid2, "artifact.bundle_manifest")
    assert last_mid2["event_type"] == "tool_execute"
    assert last_mid2["tool_name"] == "artifact.bundle_manifest"
    assert last_mid2["status"] == "idempotent"

    # 3) Error (missing canon artifact)
    try:
        artifact_bundle_manifest(
            {
                "created_at_utc": "2026-02-17T12:20:05Z",
                "canon_artifact_id": f"{canon_id}_missing",
                "bundle_artifact_id": f"{bundle_id}_missing",
                "media_type": "application/json",
            }
        )
        raise AssertionError("expected ValueError, but call succeeded")
    except ValueError:
        pass

    after = _read_jsonl(ACT_LOG)
    assert len(after) == before_n + 3, "expected exactly 1 additional engineering event after error case"

    last_after = _last_tool_event(after, "artifact.bundle_manifest")
    assert last_after["event_type"] == "tool_execute"
    assert last_after["tool_name"] == "artifact.bundle_manifest"
    assert last_after["status"] == "error"

    print(
        json.dumps(
            {
                "ok": True,
                "tool": "artifact.bundle_manifest",
                "new_events_added": 3,
                "statuses": ["success", "idempotent", "error"],
            },
            indent=2,
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
