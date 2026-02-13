# Procedure: Proof for Phase 7 Step 6 (canon select) - deterministic, append-only registry, idempotent
from __future__ import annotations

import sys
from pathlib import Path

# Ensure repo root is on sys.path so `import adam_os` works when running `python scripts/proofs/...`
REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from pathlib import Path as _Path  # noqa: E402
from uuid import uuid4  # noqa: E402

from adam_os.tools.artifact_ingest import artifact_ingest  # noqa: E402
from adam_os.tools.artifact_sanitize import artifact_sanitize  # noqa: E402
from adam_os.tools.artifact_canon_select import artifact_canon_select  # noqa: E402


ARTIFACT_ROOT = _Path(".adam_os") / "artifacts"
REGISTRY_PATH = ARTIFACT_ROOT / "artifact_registry.jsonl"


def _count_registry(artifact_id: str, kind: str) -> int:
    if not REGISTRY_PATH.exists():
        return 0
    needle_id = f"\"artifact_id\":\"{artifact_id}\""
    needle_kind = f"\"kind\":\"{kind}\""
    n = 0
    with REGISTRY_PATH.open("r", encoding="utf-8") as f:
        for line in f:
            if needle_id in line and needle_kind in line:
                n += 1
    return n


def main() -> None:
    created_at_utc = "2026-02-12T00:00:00Z"  # injected constant (no clock)

    run_id = str(uuid4())[:8]
    raw_id = f"proof-step6-raw-{run_id}"
    sanitized_id = f"proof-step6-sanitized-{run_id}"
    canon_id = f"proof-step6-canon-{run_id}"

    # Seed raw with mixed statement types
    raw_text = (
        "The sky is blue. "
        "I think this will work. "
        "What is the next step? "
        "Phase 7 requires deterministic outputs.\n"
        "Probably we should test idempotency.\n"
        "AdamOS stores artifacts under .adam_os.\n"
    )

    r0 = _count_registry(raw_id, "RAW")
    s0 = _count_registry(sanitized_id, "SANITIZED")
    c0 = _count_registry(canon_id, "BUNDLE_MANIFEST")

    ingest_out = artifact_ingest(
        {
            "content": raw_text,
            "created_at_utc": created_at_utc,
            "media_type": "text/plain",
            "artifact_id": raw_id,
        }
    )
    assert ingest_out["artifact_id"] == raw_id
    assert _count_registry(raw_id, "RAW") == r0 + 1

    sanitize_out = artifact_sanitize(
        {
            "raw_artifact_id": raw_id,
            "created_at_utc": created_at_utc,
            "sanitized_artifact_id": sanitized_id,
        }
    )
    assert sanitize_out["artifact_id"] == sanitized_id
    assert _count_registry(sanitized_id, "SANITIZED") == s0 + 1

    # First canon run (should append exactly one BUNDLE_MANIFEST record)
    canon_out_1 = artifact_canon_select(
        {
            "sanitized_artifact_id": sanitized_id,
            "created_at_utc": created_at_utc,
            "canon_artifact_id": canon_id,
        }
    )
    assert canon_out_1["artifact_id"] == canon_id
    assert canon_out_1["kind"] == "BUNDLE_MANIFEST"
    assert _count_registry(canon_id, "BUNDLE_MANIFEST") == c0 + 1

    canon_path = _Path(canon_out_1["canon_path"])
    assert canon_path.exists()
    content_1 = canon_path.read_text(encoding="utf-8")

    # Second canon run (idempotent: no new registry append, identical output)
    canon_out_2 = artifact_canon_select(
        {
            "sanitized_artifact_id": sanitized_id,
            "created_at_utc": created_at_utc,
            "canon_artifact_id": canon_id,
        }
    )
    assert canon_out_2["artifact_id"] == canon_id
    assert _count_registry(canon_id, "BUNDLE_MANIFEST") == c0 + 1

    content_2 = canon_path.read_text(encoding="utf-8")
    assert content_1 == content_2

    # Safety sanity: output must contain only SOURCE-BASED lines
    for line in content_1.splitlines():
        if not line.strip():
            continue
        assert "\"type\":\"SOURCE-BASED\"" in line

    print("PHASE 7 STEP 6 PROOF: PASS")
    print(f"RAW={raw_id}")
    print(f"SANITIZED={sanitized_id}")
    print(f"CANON={canon_id}")
    print(f"canon_path={canon_path}")


if __name__ == "__main__":
    main()
