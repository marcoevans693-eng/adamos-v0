"""
adam_os.inference.registry

Append-only inference artifact registry writer for Phase 8.

Registry file location:
- .adam_os/inference/inference_registry.jsonl

Rules:
- Append-only JSONL.
- Record schema enforced.
- No system clock reads; created_at_utc must be injected by caller.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, Optional

from adam_os.artifacts.registry import sha256_file, file_size_bytes
from adam_os.memory.canonical import canonical_dumps
from adam_os.inference.records import InferenceArtifactRecord


class InferenceArtifactRegistry:
    def __init__(self, root: Path = Path(".adam_os") / "inference") -> None:
        self.root = root
        self.registry_path = root / "inference_registry.jsonl"

    def ensure_dirs(self) -> None:
        self.root.mkdir(parents=True, exist_ok=True)

    def append(self, record: InferenceArtifactRecord) -> Dict[str, Any]:
        record.validate()
        self.ensure_dirs()
        line = canonical_dumps(record.to_dict())
        with self.registry_path.open("a", encoding="utf-8") as f:
            f.write(line)
            f.write("\n")
        return record.to_dict()

    def append_from_file(
        self,
        *,
        artifact_id: str,
        kind: str,
        created_at_utc: str,
        file_path: Path,
        media_type: str,
        parent_artifact_ids: Optional[list[str]] = None,
        notes: Optional[str] = None,
        tags: Optional[list[str]] = None,
    ) -> Dict[str, Any]:
        if parent_artifact_ids is None:
            parent_artifact_ids = []

        sha = sha256_file(file_path)
        size = file_size_bytes(file_path)

        rec = InferenceArtifactRecord(
            artifact_id=artifact_id,
            kind=kind,
            created_at_utc=created_at_utc,
            sha256=sha,
            byte_size=size,
            media_type=media_type,
            parent_artifact_ids=parent_artifact_ids,
            notes=notes,
            tags=tags,
        )
        return self.append(rec)
