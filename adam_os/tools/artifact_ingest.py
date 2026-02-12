# Procedure: Phase 7 tool - artifact.ingest (RAW artifact write + registry append; no ledger writes here)
"""
Artifact ingest tool (Phase 7)

Tool name: "artifact.ingest"

Purpose:
- Accept raw TEXT content (string-only in v0).
- Write a RAW artifact file under .adam_os/artifacts/raw/
- Append an artifact registry record (append-only JSONL).
- Return artifact_id, sha256, and paths.

This tool performs filesystem writes ONLY under the approved artifact root.
It does NOT write to the run ledger; the dispatcher owns receipts.
It does NOT call models.
It does NOT perform sanitization (that is Step 5).

Expected tool_input:
{
  "content": "<string>",
  "created_at_utc": "<iso8601 string injected>",
  "media_type": "text/plain" (optional; default "text/plain"),
  "artifact_id": "<string>" (optional; if omitted, a uuid4 is generated)
}

Returns:
{
  "artifact_id": "<id>",
  "kind": "RAW",
  "raw_path": "<path>",
  "registry_path": "<path>",
  "sha256": "<sha256 of raw file>",
  "byte_size": <int>,
  "media_type": "<string>"
}
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict
from uuid import uuid4

from adam_os.artifacts.registry import ArtifactRegistry, sha256_file, file_size_bytes


TOOL_NAME = "artifact.ingest"


def artifact_ingest(tool_input: Dict[str, Any]) -> Dict[str, Any]:
    """
    Write RAW artifact file + append artifact registry record (append-only).
    """
    if not isinstance(tool_input, dict):
        raise TypeError("tool_input must be dict")

    content = tool_input.get("content")
    if not isinstance(content, str) or not content:
        raise ValueError("tool_input.content must be a non-empty string")

    created_at_utc = tool_input.get("created_at_utc")
    if not isinstance(created_at_utc, str) or not created_at_utc.strip():
        raise ValueError("tool_input.created_at_utc must be a non-empty injected string")

    media_type = tool_input.get("media_type") or "text/plain"
    if not isinstance(media_type, str) or not media_type.strip():
        raise ValueError("tool_input.media_type must be a non-empty string")

    artifact_id = tool_input.get("artifact_id")
    if artifact_id is None:
        artifact_id = str(uuid4())
    if not isinstance(artifact_id, str) or not artifact_id.strip():
        raise ValueError("tool_input.artifact_id must be a non-empty string if provided")

    artifact_root = Path(".adam_os") / "artifacts"
    raw_dir = artifact_root / "raw"
    raw_dir.mkdir(parents=True, exist_ok=True)

    raw_path = raw_dir / f"{artifact_id}.txt"
    raw_path.write_text(content, encoding="utf-8")

    sha = sha256_file(raw_path)
    size = file_size_bytes(raw_path)

    reg = ArtifactRegistry(artifact_root=artifact_root)
    reg.append_from_file(
        artifact_id=artifact_id,
        kind="RAW",
        created_at_utc=created_at_utc,
        file_path=raw_path,
        media_type=media_type,
        parent_artifact_ids=[],
        notes="artifact.ingest",
        tags=["phase7", "raw"],
    )

    return {
        "artifact_id": artifact_id,
        "kind": "RAW",
        "raw_path": str(raw_path),
        "registry_path": str(reg.registry_path),
        "sha256": sha,
        "byte_size": size,
        "media_type": media_type,
    }
