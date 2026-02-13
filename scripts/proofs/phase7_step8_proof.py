# Procedure: Phase 7 Step 8 proof - deterministic prompt_hash + registry append-only + idempotency (robust sys.path)
from __future__ import annotations

import os
import sys
import tempfile
from pathlib import Path

# Ensure repo root is on sys.path BEFORE importing adam_os.
REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from adam_os.artifacts.registry import ArtifactRegistry, sha256_file
from adam_os.memory.canonical import canonical_dumps
from adam_os.tools.artifact_build_spec import artifact_build_spec


def _sha256_text(s: str) -> str:
    import hashlib
    return hashlib.sha256(s.encode("utf-8")).hexdigest()


def _write_bundle_manifest(tmp_root: Path, bundle_id: str, created_at_utc: str) -> Path:
    artifacts_root = tmp_root / ".adam_os" / "artifacts"
    bundles_dir = artifacts_root / "bundles"
    bundles_dir.mkdir(parents=True, exist_ok=True)

    bundle_path = bundles_dir / f"{bundle_id}.json"

    members = [
        {"artifact_id": "raw-1", "sha256": "0" * 64, "byte_size": 10, "kind": "RAW"},
        {"artifact_id": "san-1", "sha256": "1" * 64, "byte_size": 20, "kind": "SANITIZED"},
    ]

    payload = {"bundle_id": bundle_id, "kind": "BUNDLE_MANIFEST", "created_at_utc": created_at_utc, "members": members}
    payload_canon = canonical_dumps(payload)
    bundle_hash = _sha256_text(payload_canon)

    final_obj = dict(payload)
    final_obj["bundle_hash"] = bundle_hash

    bundle_path.write_text(canonical_dumps(final_obj) + "\n", encoding="utf-8")
    return bundle_path


def _registry_line_count(path: Path) -> int:
    if not path.exists():
        return 0
    return sum(1 for _ in path.open("r", encoding="utf-8"))


def main() -> None:
    created_at_utc = "2026-02-12T00:00:00Z"

    with tempfile.TemporaryDirectory() as td:
        tmp_root = Path(td)
        os.chdir(tmp_root)

        artifacts_root = Path(".adam_os") / "artifacts"
        reg = ArtifactRegistry(artifact_root=artifacts_root)

        bundle_id = "bundle-1"
        bundle_path = _write_bundle_manifest(tmp_root, bundle_id=bundle_id, created_at_utc=created_at_utc)
        reg.append_from_file(
            artifact_id=bundle_id,
            kind="BUNDLE_MANIFEST",
            created_at_utc=created_at_utc,
            file_path=bundle_path,
            media_type="application/json",
            parent_artifact_ids=["canon-1"],
            notes="proof_seed_bundle_manifest",
            tags=["phase7", "bundle_manifest"],
        )

        before_lines = _registry_line_count(reg.registry_path)

        out1 = artifact_build_spec(
            {
                "created_at_utc": created_at_utc,
                "bundle_artifact_id": bundle_id,
                "provider": "mock",
                "model": "mock-1",
                "temperature": 0.0,
                "max_tokens": 256,
                "inferred_notes": "mocked inference output for proof determinism",
            }
        )

        spec_path = Path(out1["spec_path"])
        assert spec_path.exists(), "BUILD_SPEC file not created"
        assert out1["kind"] == "BUILD_SPEC"
        assert isinstance(out1.get("prompt_hash"), str) and len(out1["prompt_hash"]) == 64
        assert isinstance(out1.get("bundle_hash"), str) and len(out1["bundle_hash"]) == 64

        mid_lines = _registry_line_count(reg.registry_path)
        assert mid_lines == before_lines + 1, "registry should append exactly one BUILD_SPEC record"

        out2 = artifact_build_spec(
            {
                "created_at_utc": created_at_utc,
                "bundle_artifact_id": bundle_id,
                "provider": "mock",
                "model": "mock-1",
                "temperature": 0.0,
                "max_tokens": 256,
                "inferred_notes": "mocked inference output for proof determinism",
            }
        )

        after_lines = _registry_line_count(reg.registry_path)
        assert after_lines == mid_lines, "idempotency failed: registry appended again"

        assert out2["prompt_hash"] == out1["prompt_hash"], "prompt_hash must be stable across runs"
        assert out2["bundle_hash"] == out1["bundle_hash"], "bundle_hash must be stable across runs"

        spec_sha = sha256_file(spec_path)
        assert spec_sha == out1["sha256"], "returned sha256 must match file sha256"

    print("phase7_step8_proof OK")


if __name__ == "__main__":
    main()
