"""
Phase 8 Step 3 tool - inference.response_emit

Tool name: "inference.response_emit"

Goal:
- Write an inference.response artifact (no provider call).
- Write ONLY under .adam_os/inference/responses/
- Append ONLY to .adam_os/inference/inference_registry.jsonl
- No ledger writes.
- Idempotent behavior.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict

from adam_os.engineering.activity_events import log_tool_execution
from adam_os.inference.registry import InferenceArtifactRegistry
from adam_os.artifacts.registry import sha256_file, file_size_bytes


TOOL_NAME = "inference.response_emit"

INFERENCE_ROOT = Path(".adam_os") / "inference"
RESPONSES_DIR = INFERENCE_ROOT / "responses"

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


def inference_response_emit(tool_input: Dict[str, Any]) -> Dict[str, Any]:
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

    output_text = tool_input.get("output_text")
    if not isinstance(output_text, str):
        raise ValueError("tool_input.output_text must be a string")

    response_id_in = tool_input.get("response_id") or f"{request_id}--response"
    if not isinstance(response_id_in, str) or not response_id_in.strip():
        raise ValueError("tool_input.response_id invalid")
    response_id = response_id_in.strip()

    media_type = tool_input.get("media_type") or DEFAULT_MEDIA_TYPE
    if not isinstance(media_type, str) or not media_type.strip():
        raise ValueError("media_type must be a non-empty string")

    created_at_utc_s = created_at_utc.strip()
    request_id_s = request_id.strip()

    RESPONSES_DIR.mkdir(parents=True, exist_ok=True)
    response_path = RESPONSES_DIR / f"{response_id}.json"

    reg = InferenceArtifactRegistry(root=INFERENCE_ROOT)

    # Idempotency gate
    if response_path.exists() and _registry_has(reg.registry_path, response_id, "INFERENCE_RESPONSE"):
        sha = sha256_file(response_path)
        size = file_size_bytes(response_path)

        log_tool_execution(
            created_at_utc=created_at_utc_s,
            tool_name=TOOL_NAME,
            status="success",
            request_id=request_id_s,
            artifact_id=response_id,
            extra={"kind": "INFERENCE_RESPONSE", "idempotent": True},
        )

        return {
            "artifact_id": response_id,
            "kind": "INFERENCE_RESPONSE",
            "response_path": str(response_path),
            "registry_path": str(reg.registry_path),
            "sha256": sha,
            "byte_size": size,
            "media_type": media_type,
        }

    obj = {
        "kind": "inference.response",
        "created_at_utc": created_at_utc_s,
        "request_id": request_id_s,
        "request_hash": request_hash,
        "snapshot_hash": snapshot_hash,
        "provider": provider.strip(),
        "model": model.strip(),
        "output_text": output_text,
    }

    txt = json.dumps(obj, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n"
    response_path.write_text(txt, encoding="utf-8")

    sha = sha256_file(response_path)
    size = file_size_bytes(response_path)

    reg.append_from_file(
        artifact_id=response_id,
        kind="INFERENCE_RESPONSE",
        created_at_utc=created_at_utc_s,
        file_path=response_path,
        media_type=media_type,
        parent_artifact_ids=[request_id_s],
        notes="inference.response_emit",
        tags=["phase8", "inference", "response"],
    )

    log_tool_execution(
        created_at_utc=created_at_utc_s,
        tool_name=TOOL_NAME,
        status="success",
        request_id=request_id_s,
        artifact_id=response_id,
        extra={"kind": "INFERENCE_RESPONSE", "idempotent": False},
    )

    return {
        "artifact_id": response_id,
        "kind": "INFERENCE_RESPONSE",
        "response_path": str(response_path),
        "registry_path": str(reg.registry_path),
        "sha256": sha,
        "byte_size": size,
        "media_type": media_type,
    }
