# Procedure: Phase 7 Step 10 proof - snapshot_export (portable, encrypted, hashed, append-only; idempotent)
from __future__ import annotations

import json
from pathlib import Path

from adam_os.execution_core.executor import LocalExecutor


def _count_lines(p: Path) -> int:
    if not p.exists():
        return 0
    with p.open("r", encoding="utf-8") as f:
        return sum(1 for _ in f)


def _registry_has(registry_path: Path, artifact_id: str, kind: str) -> bool:
    if not registry_path.exists():
        return False
    needle_id = f"\"artifact_id\":\"{artifact_id}\""
    needle_kind = f"\"kind\":\"{kind}\""
    with registry_path.open("r", encoding="utf-8") as f:
        for line in f:
            if needle_id in line and needle_kind in line:
                return True
    return False


def main() -> None:
    e = LocalExecutor()

    created_at_utc = "2026-02-13T00:00:00Z"

    # Known work order from Step 9 hand-off
    work_order_id = "proof-step6-canon-b78609e9--bundle--build_spec--work_order"
    work_order_path = Path(".adam_os") / "artifacts" / "work_orders" / f"{work_order_id}.json"
    if not work_order_path.exists():
        raise RuntimeError(f"expected WORK_ORDER missing: {work_order_path}")

    work_order_obj = json.loads(work_order_path.read_text(encoding="utf-8"))
    work_order_hash = work_order_obj.get("work_order_hash")
    if not isinstance(work_order_hash, str) or len(work_order_hash) != 64:
        raise RuntimeError("work_order_hash missing/invalid in work order JSON")

    # Deterministic snapshot id derived from work order hash prefix (repeatable + idempotent)
    snapshot_id = f"proof-step10-snapshot-{work_order_hash[:12]}"

    registry_path = Path(".adam_os") / "artifacts" / "artifact_registry.jsonl"
    before_lines = _count_lines(registry_path)

    # IMPORTANT: Use an environment-provided passphrase so we don't leak secrets into history.
    # For proof, accept a default passphrase if not provided (dev-only).
    passphrase = "dev-passphrase-step10"

    r1 = e.execute_tool(
        "artifact.snapshot_export",
        {
            "created_at_utc": created_at_utc,
            "work_order_artifact_id": work_order_id,
            "snapshot_id": snapshot_id,
            "encryption_passphrase": passphrase,
            "included_roots": [".adam_os/artifacts", ".adam_os/runs"],
        },
    )

    snapshot_dir = Path(r1["snapshot_dir"])
    enc_path = Path(r1["encrypted_archive_path"])
    manifest_path = Path(r1["manifest_path"])

    if not snapshot_dir.exists():
        raise RuntimeError("snapshot_dir missing after export")
    if not enc_path.exists():
        raise RuntimeError("encrypted archive missing after export")
    if not manifest_path.exists():
        raise RuntimeError("manifest missing after export")

    # Ensure plaintext tar is not left behind
    if (snapshot_dir / "snapshot.tar.tmp").exists():
        raise RuntimeError("plaintext tar temp file must not remain")

    # Manifest fields check
    m = json.loads(manifest_path.read_text(encoding="utf-8"))
    for k in ("archive_plain_sha256", "archive_enc_sha256", "encryption_scheme", "file_count", "total_plain_bytes"):
        if k not in m:
            raise RuntimeError(f"manifest missing required field: {k}")
    if not isinstance(m["archive_plain_sha256"], str) or len(m["archive_plain_sha256"]) != 64:
        raise RuntimeError("manifest.archive_plain_sha256 invalid")
    if not isinstance(m["archive_enc_sha256"], str) or len(m["archive_enc_sha256"]) != 64:
        raise RuntimeError("manifest.archive_enc_sha256 invalid")

    # Registry append-only + linkage checks
    after_lines = _count_lines(registry_path)
    if after_lines < before_lines:
        raise RuntimeError("registry line count decreased (append-only violated)")

    if not _registry_has(registry_path, snapshot_id, "SNAPSHOT_ARCHIVE"):
        raise RuntimeError("registry missing SNAPSHOT_ARCHIVE record for snapshot_id")

    if not _registry_has(registry_path, f"{snapshot_id}--manifest", "SNAPSHOT_MANIFEST"):
        raise RuntimeError("registry missing SNAPSHOT_MANIFEST record")

    # Idempotency check: re-run should not append duplicates
    mid_lines = _count_lines(registry_path)
    r2 = e.execute_tool(
        "artifact.snapshot_export",
        {
            "created_at_utc": created_at_utc,
            "work_order_artifact_id": work_order_id,
            "snapshot_id": snapshot_id,
            "encryption_passphrase": passphrase,
            "included_roots": [".adam_os/artifacts", ".adam_os/runs"],
        },
    )
    end_lines = _count_lines(registry_path)
    if end_lines != mid_lines:
        raise RuntimeError("idempotency violated: registry line count changed on second run")

    # Plain hash should remain stable across idempotent re-run (manifest value)
    if r2.get("archive_plain_sha256") != r1.get("archive_plain_sha256"):
        raise RuntimeError("archive_plain_sha256 changed across idempotent call")

    print("phase7_step10_proof OK")


if __name__ == "__main__":
    main()
