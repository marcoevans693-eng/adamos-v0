"""adam_os.artifacts.registry

Append-only artifact registry writer for Phase 7.

Registry file location (locked by Phase 7 plan):
- .adam_os/artifacts/artifact_registry.jsonl

Rules:
- Append-only JSONL.
- Record schema enforced.
- No system clock reads; created_at_utc must be injected by caller.
"""

from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Any, Dict, Optional

from adam_os.memory.canonical import canonical_dumps
from adam_os.artifacts.records import ArtifactRecord


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def file_size_bytes(path: Path) -> int:
    return path.stat().st_size


class ArtifactRegistry:
    def __init__(self, artifact_root: Path = Path(".adam_os") / "artifacts") -> None:
        self.artifact_root = artifact_root
        self.registry_path = artifact_root / "artifact_registry.jsonl"

    def ensure_dirs(self) -> None:
        self.artifact_root.mkdir(parents=True, exist_ok=True)
        # registry file is created on first append

    def append(self, record: ArtifactRecord) -> Dict[str, Any]:
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

        rec = ArtifactRecord(
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
