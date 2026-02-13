# Procedure: Phase 7 Step 7 proof - bundle manifest builder is deterministic and idempotent
from __future__ import annotations

import json
import os
import sys
import tempfile
from pathlib import Path

# Ensure repo root is on sys.path so `import adam_os` works when running as a script
REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT))

from adam_os.tools.artifact_ingest import artifact_ingest
from adam_os.tools.artifact_sanitize import artifact_sanitize
from adam_os.tools.artifact_canon_select import artifact_canon_select
from adam_os.tools.artifact_bundle_manifest import artifact_bundle_manifest


def _read_lines(p: Path) -> list[str]:
    if not p.exists():
        return []
    return [ln.rstrip("\n") for ln in p.read_text(encoding="utf-8").splitlines() if ln.strip()]


def _count_registry_lines(reg_path: Path) -> int:
    return len(_read_lines(reg_path))


def _load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def main() -> None:
    created_at = "2026-01-01T00:00:00Z"

    with tempfile.TemporaryDirectory() as td:
        cwd = os.getcwd()
        try:
            os.chdir(td)

            # 1) RAW ingest
            r = artifact_ingest(
                {
                    "content": "Alpha fact. Beta maybe. What is Gamma?",
                    "created_at_utc": created_at,
                    "artifact_id": "raw1",
                    "media_type": "text/plain",
                }
            )
            assert r["artifact_id"] == "raw1"

            # 2) SANITIZE
            s = artifact_sanitize(
                {
                    "raw_artifact_id": "raw1",
                    "created_at_utc": created_at,
                    "sanitized_artifact_id": "raw1--sanitized",
                }
            )
            assert s["artifact_id"] == "raw1--sanitized"

            # 3) CANON SELECT (SOURCE-BASED only)
            c = artifact_canon_select(
                {
                    "sanitized_artifact_id": "raw1--sanitized",
                    "created_at_utc": created_at,
                    "canon_artifact_id": "raw1--sanitized--canon",
                }
            )
            canon_id = c["artifact_id"]
            assert canon_id == "raw1--sanitized--canon"

            artifact_root = Path(".adam_os") / "artifacts"
            reg_path = artifact_root / "artifact_registry.jsonl"
            assert reg_path.exists()

            # 4) Step 7: Build bundle manifest object
            before = _count_registry_lines(reg_path)
            b = artifact_bundle_manifest(
                {
                    "canon_artifact_id": canon_id,
                    "created_at_utc": created_at,
                    "bundle_artifact_id": "bundle1",
                }
            )
            after = _count_registry_lines(reg_path)
            assert after == before + 1, "must append exactly one registry record"

            bundle_path = Path(b["bundle_path"])
            assert bundle_path.exists()

            obj = _load_json(bundle_path)
            assert obj["bundle_id"] == "bundle1"
            assert obj["kind"] == "BUNDLE_MANIFEST"
            assert obj["created_at_utc"] == created_at
            assert isinstance(obj["members"], list)
            assert len(obj["members"]) >= 2
            assert isinstance(obj.get("bundle_hash"), str) and len(obj["bundle_hash"]) == 64

            # Membership order should be root -> leaf for current single-parent chain:
            # raw1 -> raw1--sanitized -> raw1--sanitized--canon
            ids = [m["artifact_id"] for m in obj["members"]]
            assert ids[0] == "raw1"
            assert "raw1--sanitized" in ids
            assert canon_id in ids
            assert ids[-1] == canon_id

            # 5) Idempotency: second run should NOT append
            before2 = _count_registry_lines(reg_path)
            b2 = artifact_bundle_manifest(
                {
                    "canon_artifact_id": canon_id,
                    "created_at_utc": created_at,
                    "bundle_artifact_id": "bundle1",
                }
            )
            after2 = _count_registry_lines(reg_path)
            assert after2 == before2, "idempotent run must not append duplicate registry record"
            assert b2["artifact_id"] == "bundle1"
            assert Path(b2["bundle_path"]).read_text(encoding="utf-8") == bundle_path.read_text(encoding="utf-8")

        finally:
            os.chdir(cwd)


if __name__ == "__main__":
    main()
    print("phase7_step7_proof OK")
