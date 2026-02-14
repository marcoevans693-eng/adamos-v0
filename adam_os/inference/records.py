"""
adam_os.inference.records

Phase 8 inference artifact registry record schema + validation.

Separate from Phase 7 artifact registry to avoid mutating frozen Phase 7 ALLOWED_KINDS.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


ALLOWED_KINDS = {
    "INFERENCE_REQUEST",
    "INFERENCE_RESPONSE",
    "INFERENCE_ERROR",
    "INFERENCE_RECEIPT",
}


@dataclass(frozen=True)
class InferenceArtifactRecord:
    artifact_id: str
    kind: str
    created_at_utc: str  # injected
    sha256: str
    byte_size: int
    media_type: str
    parent_artifact_ids: List[str] = field(default_factory=list)
    notes: Optional[str] = None
    tags: Optional[List[str]] = None

    def validate(self) -> None:
        if not isinstance(self.artifact_id, str) or not self.artifact_id:
            raise ValueError("artifact_id must be a non-empty string")
        if self.kind not in ALLOWED_KINDS:
            raise ValueError(f"kind must be one of {sorted(ALLOWED_KINDS)}")
        if not isinstance(self.created_at_utc, str) or not self.created_at_utc:
            raise ValueError("created_at_utc must be a non-empty injected string")
        if not isinstance(self.sha256, str) or len(self.sha256) != 64:
            raise ValueError("sha256 must be a 64-char hex string")
        if not isinstance(self.byte_size, int) or self.byte_size < 0:
            raise ValueError("byte_size must be a non-negative int")
        if not isinstance(self.media_type, str) or not self.media_type:
            raise ValueError("media_type must be a non-empty string")
        if not isinstance(self.parent_artifact_ids, list):
            raise ValueError("parent_artifact_ids must be a list")
        for pid in self.parent_artifact_ids:
            if not isinstance(pid, str) or not pid:
                raise ValueError("parent_artifact_ids entries must be non-empty strings")
        if self.tags is not None:
            if not isinstance(self.tags, list):
                raise ValueError("tags must be a list of strings")
            for t in self.tags:
                if not isinstance(t, str) or not t:
                    raise ValueError("tags entries must be non-empty strings")

    def to_dict(self) -> Dict[str, Any]:
        d: Dict[str, Any] = {
            "artifact_id": self.artifact_id,
            "kind": self.kind,
            "created_at_utc": self.created_at_utc,
            "sha256": self.sha256,
            "byte_size": self.byte_size,
            "media_type": self.media_type,
            "parent_artifact_ids": list(self.parent_artifact_ids),
        }
        if self.notes is not None:
            d["notes"] = self.notes
        if self.tags is not None:
            d["tags"] = list(self.tags)
        return d
