# Procedure: Phase 7 tool - artifact.canon_select (select SOURCE-BASED lines; no LLM; registry append-only)
"""
Artifact canon-select tool (Phase 7 Step 6)

Tool name: "artifact.canon_select"

Deterministic Canon Selection (NO LLM):
- reads SANITIZED JSONL from .adam_os/artifacts/sanitized/<sanitized_id>.jsonl
- selects ONLY entries where obj["type"] == "SOURCE-BASED"
- preserves original order
- writes ONLY to .adam_os/artifacts/bundles/<canon_id>.jsonl
- appends ONLY to .adam_os/artifacts/artifact_registry.jsonl
- created_at_utc is injected (no clock reads)

Output kind:
- Uses "BUNDLE_MANIFEST" (because ALLOWED_KINDS is locked and does not include a CANON kind)

Idempotency:
- if canon file exists AND registry already has BUNDLE_MANIFEST record for that artifact_id,
  returns computed facts and does NOT append a duplicate record.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List, Tuple
from uuid import uuid4

from adam_os.artifacts.registry import ArtifactRegistry, sha256_file, file_size_bytes
from adam_os.engineering.activity_events import log_tool_execution
from adam_os.memory.canonical import canonical_dumps


TOOL_NAME = "artifact.canon_select"

ARTIFACT_ROOT = Path(".adam_os") / "artifacts"
SANITIZED_DIR = ARTIFACT_ROOT / "sanitized"
BUNDLES_DIR = ARTIFACT_ROOT / "bundles"

DEFAULT_MEDIA_TYPE = "application/jsonl"


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


def _load_sanitized(path: Path) -> List[Dict[str, Any]]:
    out: List[Dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as f:
        for raw_line in f:
            line = raw_line.strip()
            if not line:
                continue
            obj = json.loads(line)
            if not isinstance(obj, dict):
                raise ValueError("sanitized JSONL must contain JSON objects per line")
            t = obj.get("type")
            txt = obj.get("text")
            if not isinstance(t, str) or not t.strip():
                raise ValueError("sanitized line missing non-empty 'type'")
            if not isinstance(txt, str) or not txt.strip():
                raise ValueError("sanitized line missing non-empty 'text'")
            out.append({"type": t, "text": txt})
    return out


def artifact_canon_select(tool_input: Dict[str, Any]) -> Dict[str, Any]:
    if not isinstance(tool_input, dict):
        raise TypeError("tool_input must be dict")

    created_at_utc = tool_input.get("created_at_utc")
    if not isinstance(created_at_utc, str) or not created_at_utc.strip():
        raise ValueError("tool_input.created_at_utc must be a non-empty injected string")

    try:
        media_type = tool_input.get("media_type") or DEFAULT_MEDIA_TYPE
        if not isinstance(media_type, str) or not media_type.strip():
            raise ValueError("tool_input.media_type must be a non-empty string")

        sanitized_artifact_id = tool_input.get("sanitized_artifact_id")
        if not isinstance(sanitized_artifact_id, str) or not sanitized_artifact_id.strip():
            raise ValueError("tool_input.sanitized_artifact_id must be a non-empty string")
        sanitized_id = sanitized_artifact_id.strip()

        sanitized_path = SANITIZED_DIR / f"{sanitized_id}.jsonl"
        if not sanitized_path.exists():
            raise FileNotFoundError(f"SANITIZED artifact not found at: {sanitized_path}")

        canon_artifact_id = tool_input.get("canon_artifact_id") or f"{sanitized_id}--canon"
        if not isinstance(canon_artifact_id, str) or not canon_artifact_id.strip():
            raise ValueError("tool_input.canon_artifact_id must be a non-empty string if provided")
        canon_id = canon_artifact_id.strip()

        BUNDLES_DIR.mkdir(parents=True, exist_ok=True)
        canon_path = BUNDLES_DIR / f"{canon_id}.jsonl"

        reg = ArtifactRegistry(artifact_root=ARTIFACT_ROOT)

        # Idempotency gate (no duplicate registry append)
        if canon_path.exists() and _registry_has(reg.registry_path, canon_id, "BUNDLE_MANIFEST"):
            sha = sha256_file(canon_path)
            size = file_size_bytes(canon_path)
            result = {
                "artifact_id": canon_id,
                "kind": "BUNDLE_MANIFEST",
                "sanitized_artifact_id": sanitized_id,
                "sanitized_path": str(sanitized_path),
                "canon_path": str(canon_path),
                "registry_path": str(reg.registry_path),
                "sha256": sha,
                "byte_size": size,
                "media_type": media_type,
            }
            log_tool_execution(
                created_at_utc=created_at_utc,
                tool_name=TOOL_NAME,
                status="idempotent",
                artifact_id=canon_id,
                extra={
                    "kind": "BUNDLE_MANIFEST",
                    "media_type": media_type,
                },
            )
            return result

        # Load sanitized lines and select SOURCE-BASED only (preserve order)
        items = _load_sanitized(sanitized_path)
        selected: List[Dict[str, Any]] = []
        for obj in items:
            if obj["type"] == "SOURCE-BASED":
                selected.append(obj)

        # Write canon JSONL (canonical, deterministic)
        lines = [canonical_dumps({"type": "SOURCE-BASED", "text": o["text"]}) for o in selected]
        canon_text = ("\n".join(lines) + "\n") if lines else ""
        canon_path.write_text(canon_text, encoding="utf-8")

        sha = sha256_file(canon_path)
        size = file_size_bytes(canon_path)

        reg.append_from_file(
            artifact_id=canon_id,
            kind="BUNDLE_MANIFEST",
            created_at_utc=created_at_utc,
            file_path=canon_path,
            media_type=media_type,
            parent_artifact_ids=[sanitized_id],
            notes="artifact.canon_select",
            tags=["phase7", "canon", "bundle_manifest"],
        )

        result = {
            "artifact_id": canon_id,
            "kind": "BUNDLE_MANIFEST",
            "sanitized_artifact_id": sanitized_id,
            "sanitized_path": str(sanitized_path),
            "canon_path": str(canon_path),
            "registry_path": str(reg.registry_path),
            "sha256": sha,
            "byte_size": size,
            "media_type": media_type,
        }
        log_tool_execution(
            created_at_utc=created_at_utc,
            tool_name=TOOL_NAME,
            status="success",
            artifact_id=canon_id,
            extra={
                "kind": "BUNDLE_MANIFEST",
                "media_type": media_type,
            },
        )
        return result

    except Exception as e:
        # Best-effort error log; do not alter exception semantics.
        try:
            canon_id = locals().get("canon_id")
            log_tool_execution(
                created_at_utc=created_at_utc,
                tool_name=TOOL_NAME,
                status="error",
                artifact_id=canon_id if isinstance(canon_id, str) else None,
                extra={
                    "error_type": type(e).__name__,
                    "error_message": str(e),
                },
            )
        except Exception:
            pass
        raise
