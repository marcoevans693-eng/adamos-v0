# Procedure: Phase 7 tool - artifact.sanitize (deterministic sanitize/normalize; no LLM; registry append-only)
"""
Artifact sanitize tool (Phase 7 Step 5)

Tool name: "artifact.sanitize"

Deterministic sanitizer (NO LLM):
- reads RAW text from .adam_os/artifacts/raw/<raw_id>.txt
- emits JSONL lines: {"type": "SOURCE-BASED"|"ASSUMPTION"|"QUESTION", "text": "..."}
- writes ONLY to .adam_os/artifacts/sanitized/<sanitized_id>.jsonl
- appends ONLY to .adam_os/artifacts/artifact_registry.jsonl
- created_at_utc is injected (no clock reads)

Idempotency:
- if sanitized file exists AND registry already has SANITIZED record for that artifact_id,
  returns computed facts and does NOT append a duplicate record.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any, Dict, List, Tuple

from adam_os.artifacts.registry import ArtifactRegistry, sha256_file, file_size_bytes
from adam_os.memory.canonical import canonical_dumps


TOOL_NAME = "artifact.sanitize"

ARTIFACT_ROOT = Path(".adam_os") / "artifacts"
RAW_DIR = ARTIFACT_ROOT / "raw"
SANITIZED_DIR = ARTIFACT_ROOT / "sanitized"

DEFAULT_MEDIA_TYPE = "application/jsonl"

_Q_START = re.compile(
    r"^(what|why|how|when|where|who|which|can|could|should|would|do|does|did|is|are|am|may|might)\b",
    re.IGNORECASE,
)


def _collapse_ws(s: str) -> str:
    return re.sub(r"\s+", " ", s).strip()


def _split_statements(text: str) -> List[str]:
    if not text:
        return []

    t = text.replace("\r\n", "\n").replace("\r", "\n")
    out: List[str] = []
    for line in t.split("\n"):
        line = line.strip()
        if not line:
            continue

        parts = re.split(r"(?<=[\.\!\?])\s+", line)
        for p in parts:
            p = _collapse_ws(p)
            if p:
                out.append(p)
    return out


def _classify(stmt: str) -> str:
    s = stmt.strip()
    if s.endswith("?") or _Q_START.match(s):
        return "QUESTION"

    s_lower = s.lower()
    assumption_markers = (
        "assume",
        "assumption",
        "probably",
        "likely",
        "unlikely",
        "maybe",
        "might",
        "i think",
        "we think",
        "it seems",
        "seems",
        "estimate",
        "guess",
        "roughly",
        "approximately",
        "perhaps",
    )
    for m in assumption_markers:
        if m in s_lower:
            return "ASSUMPTION"

    return "SOURCE-BASED"


def _to_jsonl(statements: List[str]) -> str:
    lines: List[str] = []
    for stmt in statements:
        obj = {"type": _classify(stmt), "text": stmt}
        lines.append(canonical_dumps(obj))
    return ("\n".join(lines) + "\n") if lines else ""


def _ensure_within_raw_dir(raw_path: Path) -> None:
    raw_dir = RAW_DIR.resolve()
    p = raw_path.resolve()
    if raw_dir not in p.parents and p != raw_dir:
        raise ValueError("raw_path must be within .adam_os/artifacts/raw/")


def _resolve_raw(tool_input: Dict[str, Any]) -> Tuple[str, Path]:
    raw_artifact_id = tool_input.get("raw_artifact_id")
    raw_path_in = tool_input.get("raw_path")

    if raw_artifact_id is not None:
        if not isinstance(raw_artifact_id, str) or not raw_artifact_id.strip():
            raise ValueError("tool_input.raw_artifact_id must be a non-empty string if provided")
        rid = raw_artifact_id.strip()
        return rid, RAW_DIR / f"{rid}.txt"

    if raw_path_in is not None:
        if not isinstance(raw_path_in, str) or not raw_path_in.strip():
            raise ValueError("tool_input.raw_path must be a non-empty string if provided")
        p = Path(raw_path_in)
        _ensure_within_raw_dir(p)
        rid = p.stem
        if not rid:
            raise ValueError("raw_path must have a filename stem usable as raw_artifact_id")
        return rid, p

    raise ValueError("must provide tool_input.raw_artifact_id or tool_input.raw_path")


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


def artifact_sanitize(tool_input: Dict[str, Any]) -> Dict[str, Any]:
    if not isinstance(tool_input, dict):
        raise TypeError("tool_input must be dict")

    created_at_utc = tool_input.get("created_at_utc")
    if not isinstance(created_at_utc, str) or not created_at_utc.strip():
        raise ValueError("tool_input.created_at_utc must be a non-empty injected string")

    media_type = tool_input.get("media_type") or DEFAULT_MEDIA_TYPE
    if not isinstance(media_type, str) or not media_type.strip():
        raise ValueError("tool_input.media_type must be a non-empty string")

    raw_id, raw_path = _resolve_raw(tool_input)
    if not raw_path.exists():
        raise FileNotFoundError(f"RAW artifact not found at: {raw_path}")

    sanitized_artifact_id = tool_input.get("sanitized_artifact_id") or f"{raw_id}--sanitized"
    if not isinstance(sanitized_artifact_id, str) or not sanitized_artifact_id.strip():
        raise ValueError("tool_input.sanitized_artifact_id must be a non-empty string if provided")
    sanitized_id = sanitized_artifact_id.strip()

    SANITIZED_DIR.mkdir(parents=True, exist_ok=True)
    sanitized_path = SANITIZED_DIR / f"{sanitized_id}.jsonl"

    reg = ArtifactRegistry(artifact_root=ARTIFACT_ROOT)

    # Idempotency gate (no duplicate registry append)
    if sanitized_path.exists() and _registry_has(reg.registry_path, sanitized_id, "SANITIZED"):
        sha = sha256_file(sanitized_path)
        size = file_size_bytes(sanitized_path)
        return {
            "artifact_id": sanitized_id,
            "kind": "SANITIZED",
            "raw_artifact_id": raw_id,
            "raw_path": str(raw_path),
            "sanitized_path": str(sanitized_path),
            "registry_path": str(reg.registry_path),
            "sha256": sha,
            "byte_size": size,
            "media_type": media_type,
        }

    raw_text = raw_path.read_text(encoding="utf-8")
    sanitized_text = _to_jsonl(_split_statements(raw_text))
    sanitized_path.write_text(sanitized_text, encoding="utf-8")

    sha = sha256_file(sanitized_path)
    size = file_size_bytes(sanitized_path)

    reg.append_from_file(
        artifact_id=sanitized_id,
        kind="SANITIZED",
        created_at_utc=created_at_utc,
        file_path=sanitized_path,
        media_type=media_type,
        parent_artifact_ids=[raw_id],
        notes="artifact.sanitize",
        tags=["phase7", "sanitized"],
    )

    return {
        "artifact_id": sanitized_id,
        "kind": "SANITIZED",
        "raw_artifact_id": raw_id,
        "raw_path": str(raw_path),
        "sanitized_path": str(sanitized_path),
        "registry_path": str(reg.registry_path),
        "sha256": sha,
        "byte_size": size,
        "media_type": media_type,
    }
