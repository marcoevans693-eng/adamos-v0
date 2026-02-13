# Procedure: Phase 7 Step 5 proof - create RAW via artifact.ingest, sanitize via artifact.sanitize, verify idempotency + lineage
from __future__ import annotations

import json
import sys
from pathlib import Path

# Proof scripts may be run directly; inject repo root for imports.
REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from adam_os.tools.artifact_ingest import artifact_ingest
from adam_os.tools.artifact_sanitize import artifact_sanitize
from adam_os.artifacts.registry import ArtifactRegistry


def _count_lines(p: Path) -> int:
    if not p.exists():
        return 0
    with p.open("r", encoding="utf-8") as f:
        return sum(1 for _ in f)


def main() -> int:
    created_at = "2000-01-01T00:00:00Z"
    raw_id = "proof-raw-for-sanitize-1"

    artifact_root = Path(".adam_os") / "artifacts"
    reg = ArtifactRegistry(artifact_root=artifact_root)

    # 1) Ingest RAW
    raw_content = (
        "We shipped Phase 7 Step 4 today.\n"
        "I think Step 5 should be deterministic.\n"
        "What is the next step?\n"
        "Probably we should avoid LLM calls."
    )
    ingest_res = artifact_ingest(
        {
            "content": raw_content,
            "created_at_utc": created_at,
            "media_type": "text/plain",
            "artifact_id": raw_id,
        }
    )

    # 2) Sanitize once
    before_lines = _count_lines(reg.registry_path)

    sanitize_res_1 = artifact_sanitize(
        {
            "raw_artifact_id": raw_id,
            "created_at_utc": created_at,
        }
    )

    # Basic assertions (no pytest)
    assert ingest_res["artifact_id"] == raw_id
    assert sanitize_res_1["kind"] == "SANITIZED"
    assert sanitize_res_1["raw_artifact_id"] == raw_id
    assert len(sanitize_res_1["sha256"]) == 64

    sanitized_path = Path(sanitize_res_1["sanitized_path"])
    assert sanitized_path.exists(), "sanitized file missing"

    mid_lines = _count_lines(reg.registry_path)
    assert mid_lines == before_lines + 1, "expected exactly one registry append for first sanitize"

    # 3) Sanitize again (idempotency): should not append another SANITIZED row
    sanitize_res_2 = artifact_sanitize(
        {
            "raw_artifact_id": raw_id,
            "created_at_utc": created_at,
        }
    )

    after_lines = _count_lines(reg.registry_path)
    assert sanitize_res_2["sha256"] == sanitize_res_1["sha256"], "sanitize not deterministic"
    assert after_lines == mid_lines, "idempotency violated (registry line count changed on second sanitize)"

    # 4) Confirm registry tail contains sanitized id + parent linkage (best-effort scan tail)
    tail = reg.registry_path.read_text(encoding="utf-8").strip().splitlines()[-12:]
    found = False
    sanitized_id = sanitize_res_1["artifact_id"]
    for line in tail:
        if (
            f"\"artifact_id\":\"{sanitized_id}\"" in line
            and "\"kind\":\"SANITIZED\"" in line
            and f"\"parent_artifact_ids\":[\"{raw_id}\"]" in line
        ):
            found = True
            break
    assert found, "sanitized registry record not found in tail (unexpected)"

    print("PHASE7_STEP5_PROOF_OK")
    print(json.dumps({"raw_id": raw_id, "sanitized_id": sanitized_id}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
