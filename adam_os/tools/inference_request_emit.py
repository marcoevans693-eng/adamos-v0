"""
Phase 8 Step 1 tool - inference.request_emit

Tool name: "inference.request_emit"

Goal:
- Validate and build an inference.request object (SPEC-008).
- Write ONLY under .adam_os/inference/requests/
- Append ONLY to .adam_os/inference/inference_registry.jsonl
- No provider calls.
- No ledger writes.
- Idempotent behavior.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict

from adam_os.engineering.activity_events import log_tool_execution
from adam_os.inference.contracts import build_inference_request
from adam_os.inference.registry import InferenceArtifactRegistry
from adam_os.artifacts.registry import sha256_file, file_size_bytes


TOOL_NAME = "inference.request_emit"

INFERENCE_ROOT = Path(".adam_os") / "inference"
REQUESTS_DIR = INFERENCE_ROOT / "requests"

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


def inference_request_emit(tool_input: Dict[str, Any]) -> Dict[str, Any]:
    if not isinstance(tool_input, dict):
        raise TypeError("tool_input must be dict")

    try:
        req = build_inference_request(tool_input)

        created_at_utc = req["created_at_utc"]
        request_id = req["request_id"]
        media_type = tool_input.get("media_type") or DEFAULT_MEDIA_TYPE

        if not isinstance(media_type, str) or not media_type.strip():
            raise ValueError("media_type must be a non-empty string")

        REQUESTS_DIR.mkdir(parents=True, exist_ok=True)
        request_path = REQUESTS_DIR / f"{request_id}.json"

        reg = InferenceArtifactRegistry(root=INFERENCE_ROOT)

        # Idempotency gate
        if request_path.exists() and _registry_has(reg.registry_path, request_id, "INFERENCE_REQUEST"):
            sha = sha256_file(request_path)
            size = file_size_bytes(request_path)

            log_tool_execution(
                created_at_utc=created_at_utc,
                tool_name=TOOL_NAME,
                status="success",
                request_id=request_id,
                artifact_id=request_id,
                extra={"kind": "INFERENCE_REQUEST", "idempotent": True},
            )

            return {
                "artifact_id": request_id,
                "kind": "INFERENCE_REQUEST",
                "request_path": str(request_path),
                "registry_path": str(reg.registry_path),
                "sha256": sha,
                "byte_size": size,
                "media_type": media_type,
                "request_hash": req["request_hash"],
            }

        # Write canonical JSON text
        txt = json.dumps(req, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n"
        request_path.write_text(txt, encoding="utf-8")

        sha = sha256_file(request_path)
        size = file_size_bytes(request_path)

        reg.append_from_file(
            artifact_id=request_id,
            kind="INFERENCE_REQUEST",
            created_at_utc=created_at_utc,
            file_path=request_path,
            media_type=media_type,
            parent_artifact_ids=[],
            notes="inference.request_emit",
            tags=["phase8", "inference", "request"],
        )

        log_tool_execution(
            created_at_utc=created_at_utc,
            tool_name=TOOL_NAME,
            status="success",
            request_id=request_id,
            artifact_id=request_id,
            extra={"kind": "INFERENCE_REQUEST", "idempotent": False},
        )

        return {
            "artifact_id": request_id,
            "kind": "INFERENCE_REQUEST",
            "request_path": str(request_path),
            "registry_path": str(reg.registry_path),
            "sha256": sha,
            "byte_size": size,
            "media_type": media_type,
            "request_hash": req["request_hash"],
        }

    except Exception as e:
        try:
            created_at_utc = req.get("created_at_utc")  # type: ignore[name-defined]
            request_id = req.get("request_id")          # type: ignore[name-defined]
            if (
                isinstance(created_at_utc, str) and created_at_utc.strip()
                and isinstance(request_id, str) and request_id.strip()
            ):
                log_tool_execution(
                    created_at_utc=created_at_utc,
                    tool_name=TOOL_NAME,
                    status="error",
                    request_id=request_id,
                    artifact_id=request_id,
                    extra={"error_type": type(e).__name__, "error": str(e)},
                )
        except Exception:
            pass
        raise
