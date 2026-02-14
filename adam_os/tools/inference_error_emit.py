"""
Phase 8 Step 3 tool - inference.error_emit

Tool name: "inference.error_emit"

Goal:
- Write an inference.error artifact (no provider call).
- Write ONLY under .adam_os/inference/errors/
- Append ONLY to .adam_os/inference/inference_registry.jsonl
- No ledger writes.
- Idempotent behavior.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, Optional

from adam_os.inference.registry import InferenceArtifactRegistry
from adam_os.artifacts.registry import sha256_file, file_size_bytes


TOOL_NAME = "inference.error_emit"

INFERENCE_ROOT = Path(".adam_os") / "inference"
ERRORS_DIR = INFERENCE_ROOT / "errors"

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


def inference_error_emit(tool_input: Dict[str, Any]) -> Dict[str, Any]:
    if not isinstance(tool_input, dict):
        raise TypeError("tool_input must be dict")

    created_at_utc = tool_input.get("created_at_utc")
    if not isinstance(created_at_utc, str) or not created_at_utc.strip():
        raise ValueError("tool_input.created_at_utc must be injected")

    request_id = tool_input.get("request_id")
    if not isinstance(request_id, str) or not request_id.strip():
        raise ValueError("tool_input.request_id must be a non-empty string")

    request_hash = tool_input.get("request_hash")
    if not isinstance(request_hash, str) or len(request_hash) != 64:
        raise ValueError("tool_input.request_hash must be a 64-hex string")

    snapshot_hash = tool_input.get("snapshot_hash")
    if not isinstance(snapshot_hash, str) or len(snapshot_hash) != 64:
        raise ValueError("tool_input.snapshot_hash must be a 64-hex string")

    provider = tool_input.get("provider")
    if not isinstance(provider, str) or not provider.strip():
        raise ValueError("tool_input.provider must be a non-empty string")

    model = tool_input.get("model")
    if not isinstance(model, str) or not model.strip():
        raise ValueError("tool_input.model must be a non-empty string")

    error_type = tool_input.get("error_type")
    if not isinstance(error_type, str) or not error_type.strip():
        raise ValueError("tool_input.error_type must be a non-empty string")

    message = tool_input.get("message")
    if not isinstance(message, str) or not message.strip():
        raise ValueError("tool_input.message must be a non-empty string")

    details = tool_input.get("details")
    if details is not None and not isinstance(details, str):
        raise ValueError("tool_input.details must be a string if provided")

    error_id_in = tool_input.get("error_id") or f"{request_id}--error"
    if not isinstance(error_id_in, str) or not error_id_in.strip():
        raise ValueError("tool_input.error_id invalid")
    error_id = error_id_in.strip()

    media_type = tool_input.get("media_type") or DEFAULT_MEDIA_TYPE
    if not isinstance(media_type, str) or not media_type.strip():
        raise ValueError("media_type must be a non-empty string")

    ERRORS_DIR.mkdir(parents=True, exist_ok=True)
    error_path = ERRORS_DIR / f"{error_id}.json"

    reg = InferenceArtifactRegistry(root=INFERENCE_ROOT)

    # Idempotency gate
    if error_path.exists() and _registry_has(reg.registry_path, error_id, "INFERENCE_ERROR"):
        sha = sha256_file(error_path)
        size = file_size_bytes(error_path)
        return {
            "artifact_id": error_id,
            "kind": "INFERENCE_ERROR",
            "error_path": str(error_path),
            "registry_path": str(reg.registry_path),
            "sha256": sha,
            "byte_size": size,
            "media_type": media_type,
        }

    obj = {
        "kind": "inference.error",
        "created_at_utc": created_at_utc,
        "request_id": request_id.strip(),
        "request_hash": request_hash,
        "snapshot_hash": snapshot_hash,
        "provider": provider.strip(),
        "model": model.strip(),
        "error_type": error_type.strip(),
        "message": message.strip(),
    }
    if details is not None:
        obj["details"] = details

    txt = json.dumps(obj, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n"
    error_path.write_text(txt, encoding="utf-8")

    sha = sha256_file(error_path)
    size = file_size_bytes(error_path)

    reg.append_from_file(
        artifact_id=error_id,
        kind="INFERENCE_ERROR",
        created_at_utc=created_at_utc,
        file_path=error_path,
        media_type=media_type,
        parent_artifact_ids=[request_id.strip()],
        notes="inference.error_emit",
        tags=["phase8", "inference", "error"],
    )

    return {
        "artifact_id": error_id,
        "kind": "INFERENCE_ERROR",
        "error_path": str(error_path),
        "registry_path": str(reg.registry_path),
        "sha256": sha,
        "byte_size": size,
        "media_type": media_type,
    }
