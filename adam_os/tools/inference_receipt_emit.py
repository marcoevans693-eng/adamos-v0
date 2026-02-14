"""
Phase 8 Step 5 tool - inference.receipt_emit

Tool name: "inference.receipt_emit"

Goal:
- Write an inference.receipt artifact (no provider call).
- Bind request + provider/model + snapshot + response|error into a deterministic receipt.
- Write ONLY under .adam_os/inference/receipts/
- Append ONLY to .adam_os/inference/inference_registry.jsonl
- No ledger writes.
- Idempotent behavior.
- Fail-closed on missing referenced artifacts.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, Optional

from adam_os.inference.registry import InferenceArtifactRegistry
from adam_os.memory.canonical import canonical_dumps, sha256_hex
from adam_os.artifacts.registry import sha256_file, file_size_bytes


TOOL_NAME = "inference.receipt_emit"

INFERENCE_ROOT = Path(".adam_os") / "inference"
REQUESTS_DIR = INFERENCE_ROOT / "requests"
RESPONSES_DIR = INFERENCE_ROOT / "responses"
ERRORS_DIR = INFERENCE_ROOT / "errors"
RECEIPTS_DIR = INFERENCE_ROOT / "receipts"

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


def _is_hex64(s: str) -> bool:
    if not isinstance(s, str) or len(s) != 64:
        return False
    try:
        int(s, 16)
        return True
    except Exception:
        return False


def inference_receipt_emit(tool_input: Dict[str, Any]) -> Dict[str, Any]:
    if not isinstance(tool_input, dict):
        raise TypeError("tool_input must be dict")

    created_at_utc = tool_input.get("created_at_utc")
    if not isinstance(created_at_utc, str) or not created_at_utc.strip():
        raise ValueError("tool_input.created_at_utc must be injected")

    request_id = tool_input.get("request_id")
    if not isinstance(request_id, str) or not request_id.strip():
        raise ValueError("tool_input.request_id must be a non-empty string")
    request_id = request_id.strip()

    request_hash = tool_input.get("request_hash")
    if not isinstance(request_hash, str) or not _is_hex64(request_hash):
        raise ValueError("tool_input.request_hash must be a 64-hex string")

    snapshot_hash = tool_input.get("snapshot_hash")
    if not isinstance(snapshot_hash, str) or not _is_hex64(snapshot_hash):
        raise ValueError("tool_input.snapshot_hash must be a 64-hex string")

    provider = tool_input.get("provider")
    if not isinstance(provider, str) or not provider.strip():
        raise ValueError("tool_input.provider must be a non-empty string")
    provider = provider.strip()

    model = tool_input.get("model")
    if not isinstance(model, str) or not model.strip():
        raise ValueError("tool_input.model must be a non-empty string")
    model = model.strip()

    response_id = tool_input.get("response_id")
    error_id = tool_input.get("error_id")

    if response_id is not None and (not isinstance(response_id, str) or not response_id.strip()):
        raise ValueError("tool_input.response_id invalid if provided")
    if error_id is not None and (not isinstance(error_id, str) or not error_id.strip()):
        raise ValueError("tool_input.error_id invalid if provided")

    if bool(response_id) == bool(error_id):
        raise ValueError("receipt_emit: exactly one of response_id or error_id must be provided")

    response_id_s: Optional[str] = response_id.strip() if isinstance(response_id, str) else None
    error_id_s: Optional[str] = error_id.strip() if isinstance(error_id, str) else None

    receipt_id_in = tool_input.get("receipt_id") or f"{request_id}--receipt"
    if not isinstance(receipt_id_in, str) or not receipt_id_in.strip():
        raise ValueError("tool_input.receipt_id invalid")
    receipt_id = receipt_id_in.strip()

    media_type = tool_input.get("media_type") or DEFAULT_MEDIA_TYPE
    if not isinstance(media_type, str) or not media_type.strip():
        raise ValueError("media_type must be a non-empty string")

    # Fail-closed: referenced artifacts must exist on disk (contract binding)
    request_path = REQUESTS_DIR / f"{request_id}.json"
    if not request_path.exists():
        raise ValueError(f"receipt_emit: missing request artifact file: {request_path}")

    if response_id_s is not None:
        result_kind = "response"
        result_id = response_id_s
        result_path = RESPONSES_DIR / f"{result_id}.json"
    else:
        result_kind = "error"
        result_id = error_id_s  # type: ignore[assignment]
        result_path = ERRORS_DIR / f"{result_id}.json"

    if not result_path.exists():
        raise ValueError(f"receipt_emit: missing {result_kind} artifact file: {result_path}")

    RECEIPTS_DIR.mkdir(parents=True, exist_ok=True)
    receipt_path = RECEIPTS_DIR / f"{receipt_id}.json"

    reg = InferenceArtifactRegistry(root=INFERENCE_ROOT)

    # Idempotency gate
    if receipt_path.exists() and _registry_has(reg.registry_path, receipt_id, "INFERENCE_RECEIPT"):
        sha = sha256_file(receipt_path)
        size = file_size_bytes(receipt_path)
        return {
            "artifact_id": receipt_id,
            "kind": "INFERENCE_RECEIPT",
            "receipt_path": str(receipt_path),
            "registry_path": str(reg.registry_path),
            "sha256": sha,
            "byte_size": size,
            "media_type": media_type,
        }

    # Compute referenced sha256 (file sha, deterministic)
    request_sha256 = sha256_file(request_path)
    result_sha256 = sha256_file(result_path)

    # Receipt payload (canonical, then receipt_hash)
    base: Dict[str, Any] = {
        "kind": "inference.receipt",
        "created_at_utc": created_at_utc,
        "request_id": request_id,
        "request_hash": request_hash,
        "snapshot_hash": snapshot_hash,
        "provider": provider,
        "model": model,
        "result": {
            "kind": result_kind,
            "artifact_id": result_id,
        },
        "inputs_sha256": {
            "request_sha256": request_sha256,
            "result_sha256": result_sha256,
        },
    }

    receipt_hash = sha256_hex(canonical_dumps(base))
    obj = dict(base)
    obj["receipt_hash"] = receipt_hash

    txt = json.dumps(obj, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n"
    receipt_path.write_text(txt, encoding="utf-8")

    sha = sha256_file(receipt_path)
    size = file_size_bytes(receipt_path)

    reg.append_from_file(
        artifact_id=receipt_id,
        kind="INFERENCE_RECEIPT",
        created_at_utc=created_at_utc,
        file_path=receipt_path,
        media_type=media_type,
        parent_artifact_ids=[request_id, result_id],
        notes="inference.receipt_emit",
        tags=["phase8", "inference", "receipt"],
    )

    return {
        "artifact_id": receipt_id,
        "kind": "INFERENCE_RECEIPT",
        "receipt_path": str(receipt_path),
        "registry_path": str(reg.registry_path),
        "sha256": sha,
        "byte_size": size,
        "media_type": media_type,
        "receipt_hash": receipt_hash,
        "request_sha256": request_sha256,
        "result_sha256": result_sha256,
    }
