"""scripts.proofs.phase7_step3_proof

Proof: Phase 7 Step 3 artifact registry is append-only + schema-valid.

This proof:
- Creates a small RAW artifact file under .adam_os/artifacts/raw/
- Appends 2 registry records referencing files
- Verifies registry grows by exactly 2 lines
- Verifies each line parses as valid ArtifactRecord
"""

from __future__ import annotations

import json
from pathlib import Path

# Ensure repo root is on sys.path so `import adam_os` works when run as a script.
import sys
from pathlib import Path as _Path
sys.path.insert(0, str(_Path(__file__).resolve().parents[2]))

from adam_os.artifacts.registry import ArtifactRegistry
from adam_os.artifacts.records import ArtifactRecord


def main() -> None:
    artifact_root = Path(".adam_os") / "artifacts"
    raw_dir = artifact_root / "raw"
    raw_dir.mkdir(parents=True, exist_ok=True)

    # injected time placeholder for proof (caller-provided; no system clock reads)
    created_at_utc = "2000-01-01T00:00:00Z"

    reg = ArtifactRegistry(artifact_root=artifact_root)

    registry_path = reg.registry_path
    before = 0
    if registry_path.exists():
        before = sum(1 for _ in registry_path.open("r", encoding="utf-8"))

    # create two small files
    f1 = raw_dir / "proof_raw_1.txt"
    f2 = raw_dir / "proof_raw_2.txt"
    f1.write_text("phase7 step3 proof file 1\n", encoding="utf-8")
    f2.write_text("phase7 step3 proof file 2\n", encoding="utf-8")

    reg.append_from_file(
        artifact_id="proof-artifact-1",
        kind="RAW",
        created_at_utc=created_at_utc,
        file_path=f1,
        media_type="text/plain",
        parent_artifact_ids=[],
        notes="phase7 step3 proof",
        tags=["proof", "phase7", "step3"],
    )

    reg.append_from_file(
        artifact_id="proof-artifact-2",
        kind="RAW",
        created_at_utc=created_at_utc,
        file_path=f2,
        media_type="text/plain",
        parent_artifact_ids=[],
        notes="phase7 step3 proof",
        tags=["proof", "phase7", "step3"],
    )

    after = sum(1 for _ in registry_path.open("r", encoding="utf-8"))

    if after != before + 2:
        raise SystemExit(f"FAIL: registry line count expected {before+2}, got {after}")

    # validate the last two lines parse as ArtifactRecord
    lines = registry_path.read_text(encoding="utf-8").splitlines()
    for i in (-2, -1):
        d = json.loads(lines[i])
        ArtifactRecord.from_dict(d)

    print("OK: phase7_step3_proof passed")
    print(f"registry_path={registry_path}")
    print(f"before_lines={before} after_lines={after}")


if __name__ == "__main__":
    main()
