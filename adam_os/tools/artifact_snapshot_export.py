# Procedure: Phase 7 Step 10 tool - artifact.snapshot_export (encrypted snapshot archive + manifest; registry append-only)
"""
Artifact snapshot-export tool (Phase 7 Step 10)

Tool name: "artifact.snapshot_export"

Goal:
- Create a portable snapshot archive that includes:
    - .adam_os/artifacts/
    - .adam_os/runs/
  (canon selection artifacts are included as part of artifacts/)
- Encrypt the archive
- Hash plaintext archive bytes and encrypted bytes
- Write ONLY under .adam_os/artifacts/snapshots/<snapshot_id>/
- Append ONLY to .adam_os/artifacts/artifact_registry.jsonl
- Preserve lineage by linking snapshot artifacts to the WORK_ORDER parent

Determinism rule:
- The plaintext TAR bytes must be deterministic when inputs are unchanged.
- The encrypted bytes may vary across runs (salt/IV), but MUST be hashed and recorded.

No plaintext persistence rule:
- A plaintext tar may exist temporarily during creation, but MUST NOT remain on disk after success.
"""

from __future__ import annotations

import json
import os
import subprocess
import tarfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Tuple

from adam_os.artifacts.registry import ArtifactRegistry, sha256_file, file_size_bytes
from adam_os.memory.canonical import canonical_dumps
from adam_os.engineering.activity_events import log_tool_execution


TOOL_NAME = "artifact.snapshot_export"

ARTIFACT_ROOT = Path(".adam_os") / "artifacts"
SNAPSHOTS_DIR = ARTIFACT_ROOT / "snapshots"
WORK_ORDERS_DIR = ARTIFACT_ROOT / "work_orders"

DEFAULT_MEDIA_TYPE_ARCHIVE = "application/octet-stream"
DEFAULT_MEDIA_TYPE_MANIFEST = "application/json"

DEFAULT_ENCRYPTION_SCHEME = "openssl-enc-aes-256-cbc-pbkdf2-salt"


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


def _ensure_within_repo(p: Path) -> None:
    # Snapshot inputs must remain within repo root (no path escape)
    root = Path(".").resolve()
    rp = p.resolve()
    if rp == root:
        return
    if root not in rp.parents:
        raise ValueError("input root must be within repo root")


def _collect_files(roots: List[Path]) -> List[Tuple[Path, str]]:
    """
    Return sorted list of (abs_path, arcname) where arcname is repo-relative posix path.
    Deterministic ordering: arcname sort.
    """
    repo_root = Path(".").resolve()
    items: List[Tuple[Path, str]] = []

    for r in roots:
        _ensure_within_repo(r)
        if not r.exists():
            continue
        if r.is_file():
            rel = r.resolve().relative_to(repo_root).as_posix()
            items.append((r, rel))
            continue
        for fp in r.rglob("*"):
            if fp.is_dir():
                continue
            rel = fp.resolve().relative_to(repo_root).as_posix()
            items.append((fp, rel))

    # Sort by archive name for deterministic tar ordering
    items.sort(key=lambda t: t[1])
    return items


def _add_file_deterministic(tf: tarfile.TarFile, file_path: Path, arcname: str) -> None:
    """
    Add a single file with deterministic tar metadata.
    """
    st = file_path.stat()

    ti = tarfile.TarInfo(name=arcname)
    ti.size = st.st_size
    ti.mtime = 0
    ti.uid = 0
    ti.gid = 0
    ti.uname = ""
    ti.gname = ""
    # Keep mode stable based on actual file mode (deterministic for the same repo state)
    ti.mode = int(st.st_mode) & 0o777

    with file_path.open("rb") as f:
        tf.addfile(ti, fileobj=f)


def _build_plain_tar(tar_path: Path, roots: List[Path]) -> Dict[str, Any]:
    """
    Build deterministic tar archive at tar_path.
    Returns: {file_count, total_bytes}
    """
    files = _collect_files(roots)

    tar_path.parent.mkdir(parents=True, exist_ok=True)

    # Use GNU tar format for broad compatibility; determinism enforced via TarInfo fields.
    with tarfile.open(tar_path, mode="w", format=tarfile.GNU_FORMAT) as tf:
        for fp, arcname in files:
            _add_file_deterministic(tf, fp, arcname)

    total = sum(fp.stat().st_size for fp, _ in files)
    return {"file_count": len(files), "total_bytes": int(total)}


def _encrypt_openssl_aes_256_cbc_pbkdf2_salt(
    *,
    plaintext_path: Path,
    encrypted_path: Path,
    passphrase: str,
) -> None:
    """
    Encrypt using OpenSSL enc with PBKDF2 + salt.
    Ciphertext will be non-deterministic (salt), which is expected and recorded via hash.
    """
    if not passphrase:
        raise ValueError("encryption_passphrase must be non-empty")

    cmd = [
        "openssl",
        "enc",
        "-aes-256-cbc",
        "-pbkdf2",
        "-salt",
        "-pass",
        f"pass:{passphrase}",
        "-in",
        str(plaintext_path),
        "-out",
        str(encrypted_path),
    ]
    proc = subprocess.run(cmd, capture_output=True, text=True)
    if proc.returncode != 0:
        stderr = (proc.stderr or "").strip()
        raise RuntimeError(f"openssl enc failed: {stderr or 'unknown error'}")


def artifact_snapshot_export(tool_input: Dict[str, Any]) -> Dict[str, Any]:
    if not isinstance(tool_input, dict):
        raise TypeError("tool_input must be dict")

    created_at_utc = tool_input.get("created_at_utc")
    if not isinstance(created_at_utc, str) or not created_at_utc.strip():
        raise ValueError("tool_input.created_at_utc must be a non-empty injected string")

    work_order_artifact_id = tool_input.get("work_order_artifact_id")
    if not isinstance(work_order_artifact_id, str) or not work_order_artifact_id.strip():
        raise ValueError("tool_input.work_order_artifact_id must be a non-empty string")
    work_order_id = work_order_artifact_id.strip()

    encryption_passphrase = tool_input.get("encryption_passphrase")
    if not isinstance(encryption_passphrase, str) or not encryption_passphrase.strip():
        raise ValueError("tool_input.encryption_passphrase must be a non-empty string")

    snapshot_id_in = tool_input.get("snapshot_id")
    if snapshot_id_in is None:
        snapshot_id_in = f"{work_order_id}--snapshot"
    if not isinstance(snapshot_id_in, str) or not snapshot_id_in.strip():
        raise ValueError("tool_input.snapshot_id must be a non-empty string if provided")
    snapshot_id = snapshot_id_in.strip()

    media_type_archive = tool_input.get("media_type_archive") or DEFAULT_MEDIA_TYPE_ARCHIVE
    media_type_manifest = tool_input.get("media_type_manifest") or DEFAULT_MEDIA_TYPE_MANIFEST

    if not isinstance(media_type_archive, str) or not media_type_archive.strip():
        raise ValueError("media_type_archive must be a non-empty string")
    if not isinstance(media_type_manifest, str) or not media_type_manifest.strip():
        raise ValueError("media_type_manifest must be a non-empty string")

    encryption_scheme = tool_input.get("encryption_scheme") or DEFAULT_ENCRYPTION_SCHEME
    if not isinstance(encryption_scheme, str) or not encryption_scheme.strip():
        raise ValueError("encryption_scheme must be a non-empty string")

    included_roots_in = tool_input.get("included_roots") or [".adam_os/artifacts", ".adam_os/runs"]
    if not isinstance(included_roots_in, list) or any((not isinstance(x, str) or not x.strip()) for x in included_roots_in):
        raise ValueError("included_roots must be a list of non-empty strings")

    included_roots = [Path(x.strip()) for x in included_roots_in]

    # Validate work order exists (parent anchor)
    work_order_path = WORK_ORDERS_DIR / f"{work_order_id}.json"
    if not work_order_path.exists():
        raise FileNotFoundError(f"WORK_ORDER not found: {work_order_path}")

    SNAPSHOTS_DIR.mkdir(parents=True, exist_ok=True)
    snapshot_dir = SNAPSHOTS_DIR / snapshot_id
    enc_path = snapshot_dir / "snapshot.enc"
    manifest_path = snapshot_dir / "snapshot_manifest.json"

    reg = ArtifactRegistry(artifact_root=ARTIFACT_ROOT)

    # Idempotency gate:
    # If directory exists and registry already has SNAPSHOT_ARCHIVE for snapshot_id, return facts from manifest.
    if snapshot_dir.exists():
        if enc_path.exists() and manifest_path.exists() and _registry_has(reg.registry_path, snapshot_id, "SNAPSHOT_ARCHIVE"):
            sha_enc = sha256_file(enc_path)
            size_enc = file_size_bytes(enc_path)
            try:
                m = json.loads(manifest_path.read_text(encoding="utf-8"))
            except Exception:
                m = {}
            return {
                "snapshot_id": snapshot_id,
                "kind": "SNAPSHOT_ARCHIVE",
                "snapshot_dir": str(snapshot_dir),
                "encrypted_archive_path": str(enc_path),
                "manifest_path": str(manifest_path),
                "registry_path": str(reg.registry_path),
                "archive_plain_sha256": m.get("archive_plain_sha256"),
                "archive_enc_sha256": sha_enc,
                "byte_size_enc": size_enc,
                "encryption_scheme": m.get("encryption_scheme"),
            }
        raise ValueError("snapshot directory already exists without valid registry-backed idempotency")

    # Create new snapshot directory (must be unique; no overwrite)
    snapshot_dir.mkdir(parents=True, exist_ok=False)

    # Plaintext tar is temporary and must be removed on success.
    plain_tar_path = snapshot_dir / "snapshot.tar.tmp"

    try:
        # Build deterministic plaintext tar (under snapshots dir only)
        stats = _build_plain_tar(plain_tar_path, included_roots)
        total_plain_bytes = file_size_bytes(plain_tar_path)
        archive_plain_sha = sha256_file(plain_tar_path)

        # Encrypt archive (ciphertext non-deterministic expected)
        _encrypt_openssl_aes_256_cbc_pbkdf2_salt(
            plaintext_path=plain_tar_path,
            encrypted_path=enc_path,
            passphrase=encryption_passphrase.strip(),
        )
        archive_enc_sha = sha256_file(enc_path)
        enc_size = file_size_bytes(enc_path)

        # Remove plaintext tar (no plaintext persistence after success)
        if plain_tar_path.exists():
            plain_tar_path.unlink()

        # Read work order for lineage metadata (no mutation)
        work_order_obj = json.loads(work_order_path.read_text(encoding="utf-8"))
        work_order_sha = sha256_file(work_order_path)

        lineage = work_order_obj.get("lineage", {})
        work_order_hash = work_order_obj.get("work_order_hash")

        manifest_obj: Dict[str, Any] = {
            "snapshot_id": snapshot_id,
            "kind": "SNAPSHOT_MANIFEST",
            "created_at_utc": created_at_utc,
            "included_roots": [p.as_posix() for p in included_roots],
            "file_count": int(stats["file_count"]),
            "total_plain_bytes": int(total_plain_bytes),
            "archive_plain_sha256": archive_plain_sha,
            "archive_enc_sha256": archive_enc_sha,
            "encryption_scheme": encryption_scheme,
            "parents": {
                "work_order_artifact_id": work_order_id,
                "work_order_sha256": work_order_sha,
                "work_order_hash": work_order_hash,
                "build_spec_artifact_id": lineage.get("build_spec_artifact_id"),
                "build_spec_sha256": lineage.get("build_spec_sha256"),
                "bundle_hash": lineage.get("bundle_hash"),
                "prompt_hash": lineage.get("prompt_hash"),
            },
            "notes": "artifact.snapshot_export",
            "tags": ["phase7", "snapshot", "encrypted", "append_only"],
        }

        manifest_text = canonical_dumps(manifest_obj) + "\n"
        manifest_path.write_text(manifest_text, encoding="utf-8")

        # Registry append (append-only): archive + manifest
        reg.append_from_file(
            artifact_id=snapshot_id,
            kind="SNAPSHOT_ARCHIVE",
            created_at_utc=created_at_utc,
            file_path=enc_path,
            media_type=media_type_archive.strip(),
            parent_artifact_ids=[work_order_id],
            notes="artifact.snapshot_export",
            tags=["phase7", "snapshot_archive"],
        )

        manifest_artifact_id = f"{snapshot_id}--manifest"
        reg.append_from_file(
            artifact_id=manifest_artifact_id,
            kind="SNAPSHOT_MANIFEST",
            created_at_utc=created_at_utc,
            file_path=manifest_path,
            media_type=media_type_manifest.strip(),
            parent_artifact_ids=[work_order_id],
            notes="artifact.snapshot_export",
            tags=["phase7", "snapshot_manifest"],
        )

        return {
            "snapshot_id": snapshot_id,
            "kind": "SNAPSHOT_ARCHIVE",
            "snapshot_dir": str(snapshot_dir),
            "encrypted_archive_path": str(enc_path),
            "manifest_path": str(manifest_path),
            "registry_path": str(reg.registry_path),
            "archive_plain_sha256": archive_plain_sha,
            "archive_enc_sha256": archive_enc_sha,
            "byte_size_enc": int(enc_size),
            "total_plain_bytes": int(total_plain_bytes),
            "file_count": int(stats["file_count"]),
            "encryption_scheme": encryption_scheme,
            "work_order_artifact_id": work_order_id,
        }

    finally:
        # Best-effort cleanup of plaintext tar (never leave it behind on success)
        if plain_tar_path.exists():
            try:
                plain_tar_path.unlink()
            except Exception:
                pass
