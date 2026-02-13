# Procedure: Phase 7 tool - artifact.bundle_manifest (build structured bundle manifest; no LLM; registry append-only)
"""
Artifact bundle-manifest tool (Phase 7 Step 7)

Tool name: "artifact.bundle_manifest"

Deterministic bundle manifest builder (NO LLM):
- input: canon_artifact_id (Step 6 output artifact id)
- reads artifact_registry.jsonl to resolve lineage + metadata (sha256/size/kind)
- builds a structured manifest object:
    {
      "bundle_id": "...",
      "kind": "BUNDLE_MANIFEST",
      "created_at_utc": "...",
      "members": [
        {"artifact_id": "...", "sha256": "...", "byte_size": 123, "kind": "..."},
        ...
      ],
      "bundle_hash": "..."   # sha256 of canonical manifest payload (see compute rule)
    }
- writes ONLY to .adam_os/artifacts/bundles/<bundle_id>.json
- appends ONLY to .adam_os/artifacts/artifact_registry.jsonl
- created_at_utc is injected (no clock reads)

Membership (deterministic):
- Start from canon_artifact_id
- Walk parent_artifact_ids through the registry until no parent remains
- Emit ordered members from oldest ancestor -> canon artifact
- De-duplicate by artifact_id while preserving first-seen order (should not occur unless registry is malformed)

Idempotency:
- if bundle file exists AND registry already has BUNDLE_MANIFEST record for bundle_id,
  returns computed facts and does NOT append a duplicate record.
"""

from __future__ import annotations

import json
import hashlib
from pathlib import Path
from typing import Any, Dict, List, Optional

from adam_os.artifacts.registry import ArtifactRegistry, sha256_file, file_size_bytes
from adam_os.memory.canonical import canonical_dumps


TOOL_NAME = "artifact.bundle_manifest"

ARTIFACT_ROOT = Path(".adam_os") / "artifacts"
BUNDLES_DIR = ARTIFACT_ROOT / "bundles"

DEFAULT_MEDIA_TYPE = "application/json"


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


def _load_registry_records(registry_path: Path) -> Dict[str, Dict[str, Any]]:
    """
    Load artifact_registry.jsonl into a dict keyed by artifact_id.
    If duplicate artifact_ids exist (should not), last one wins.
    """
    out: Dict[str, Dict[str, Any]] = {}
    if not registry_path.exists():
        return out
    with registry_path.open("r", encoding="utf-8") as f:
        for raw_line in f:
            line = raw_line.strip()
            if not line:
                continue
            obj = json.loads(line)
            if not isinstance(obj, dict):
                raise ValueError("artifact registry must contain JSON objects per line")
            aid = obj.get("artifact_id")
            if not isinstance(aid, str) or not aid.strip():
                raise ValueError("artifact registry record missing non-empty artifact_id")
            out[aid] = obj
    return out


def _resolve_lineage(
    records_by_id: Dict[str, Dict[str, Any]],
    leaf_artifact_id: str,
) -> List[Dict[str, Any]]:
    """
    Walk parents from leaf up to roots, then return ordered root->leaf list.
    """
    chain: List[Dict[str, Any]] = []
    seen: set[str] = set()

    current = leaf_artifact_id
    while True:
        if current in seen:
            raise ValueError("cycle detected in parent_artifact_ids")
        seen.add(current)

        rec = records_by_id.get(current)
        if rec is None:
            raise ValueError(f"artifact_id not found in registry: {current}")
        chain.append(rec)

        parents = rec.get("parent_artifact_ids", [])
        if not parents:
            break
        if not isinstance(parents, list) or any((not isinstance(p, str) or not p) for p in parents):
            raise ValueError("parent_artifact_ids must be a list of non-empty strings")

        # Deterministic rule: follow the FIRST parent only for lineage walk.
        # (This matches current pipeline which produces single-parent lineage for Step 4–6.)
        current = parents[0]

    chain.reverse()  # root -> leaf
    return chain


def _members_from_chain(chain: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    members: List[Dict[str, Any]] = []
    seen: set[str] = set()

    for rec in chain:
        aid = rec["artifact_id"]
        if aid in seen:
            continue
        seen.add(aid)

        kind = rec.get("kind")
        sha = rec.get("sha256")
        size = rec.get("byte_size")

        if not isinstance(kind, str) or not kind.strip():
            raise ValueError("registry record missing non-empty kind")
        if not isinstance(sha, str) or len(sha) != 64:
            raise ValueError("registry record missing valid sha256")
        if not isinstance(size, int) or size < 0:
            raise ValueError("registry record missing valid byte_size")

        members.append(
            {
                "artifact_id": aid,
                "sha256": sha,
                "byte_size": int(size),
                "kind": kind,
            }
        )

    return members


def _sha256_text(s: str) -> str:
    return hashlib.sha256(s.encode("utf-8")).hexdigest()


def artifact_bundle_manifest(tool_input: Dict[str, Any]) -> Dict[str, Any]:
    if not isinstance(tool_input, dict):
        raise TypeError("tool_input must be dict")

    created_at_utc = tool_input.get("created_at_utc")
    if not isinstance(created_at_utc, str) or not created_at_utc.strip():
        raise ValueError("tool_input.created_at_utc must be a non-empty injected string")

    media_type = tool_input.get("media_type") or DEFAULT_MEDIA_TYPE
    if not isinstance(media_type, str) or not media_type.strip():
        raise ValueError("tool_input.media_type must be a non-empty string")

    canon_artifact_id = tool_input.get("canon_artifact_id")
    if not isinstance(canon_artifact_id, str) or not canon_artifact_id.strip():
        raise ValueError("tool_input.canon_artifact_id must be a non-empty string")
    canon_id = canon_artifact_id.strip()

    bundle_artifact_id = tool_input.get("bundle_artifact_id") or f"{canon_id}--bundle"
    if not isinstance(bundle_artifact_id, str) or not bundle_artifact_id.strip():
        raise ValueError("tool_input.bundle_artifact_id must be a non-empty string if provided")
    bundle_id = bundle_artifact_id.strip()

    BUNDLES_DIR.mkdir(parents=True, exist_ok=True)
    bundle_path = BUNDLES_DIR / f"{bundle_id}.json"

    reg = ArtifactRegistry(artifact_root=ARTIFACT_ROOT)

    # Idempotency gate (no duplicate registry append)
    if bundle_path.exists() and _registry_has(reg.registry_path, bundle_id, "BUNDLE_MANIFEST"):
        sha = sha256_file(bundle_path)
        size = file_size_bytes(bundle_path)
        # Best-effort read of bundle_hash from file (optional)
        try:
            obj = json.loads(bundle_path.read_text(encoding="utf-8"))
            bundle_hash = obj.get("bundle_hash")
        except Exception:
            bundle_hash = None
        return {
            "artifact_id": bundle_id,
            "kind": "BUNDLE_MANIFEST",
            "canon_artifact_id": canon_id,
            "bundle_path": str(bundle_path),
            "registry_path": str(reg.registry_path),
            "sha256": sha,
            "byte_size": size,
            "media_type": media_type,
            "bundle_hash": bundle_hash,
        }

    # Resolve lineage via registry records (not by reading artifact blobs)
    records_by_id = _load_registry_records(reg.registry_path)
    chain = _resolve_lineage(records_by_id, canon_id)
    members = _members_from_chain(chain)

    # Build canonical payload for hashing (exclude bundle_hash to avoid circularity)
    payload = {
        "bundle_id": bundle_id,
        "kind": "BUNDLE_MANIFEST",
        "created_at_utc": created_at_utc,
        "members": members,
    }
    payload_canon = canonical_dumps(payload)
    bundle_hash = _sha256_text(payload_canon)

    final_obj = dict(payload)
    final_obj["bundle_hash"] = bundle_hash

    bundle_text = canonical_dumps(final_obj) + "\n"
    bundle_path.write_text(bundle_text, encoding="utf-8")

    sha = sha256_file(bundle_path)
    size = file_size_bytes(bundle_path)

    reg.append_from_file(
        artifact_id=bundle_id,
        kind="BUNDLE_MANIFEST",
        created_at_utc=created_at_utc,
        file_path=bundle_path,
        media_type=media_type,
        parent_artifact_ids=[canon_id],
        notes="artifact.bundle_manifest",
        tags=["phase7", "bundle_manifest", "manifest_object"],
    )

    return {
        "artifact_id": bundle_id,
        "kind": "BUNDLE_MANIFEST",
        "canon_artifact_id": canon_id,
        "bundle_path": str(bundle_path),
        "registry_path": str(reg.registry_path),
        "sha256": sha,
        "byte_size": size,
        "media_type": media_type,
        "bundle_hash": bundle_hash,
        "member_count": len(members),
    }
