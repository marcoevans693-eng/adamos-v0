"""
Phase 8 Step 6 tool - inference.replay

Tool name: "inference.replay"

Goal:
- Deterministically verify a previously emitted INFERENCE_RECEIPT.
- Recompute sha256 of referenced artifacts.
- Recompute receipt_hash from canonical payload.
- Fail-closed on any mismatch.
- No writes.
- No registry mutation.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict

from adam_os.memory.canonical import canonical_dumps, sha256_hex
from adam_os.artifacts.registry import sha256_file


TOOL_NAME = "inference.replay"

INFERENCE_ROOT = Path(".adam_os") / "inference"
RECEIPTS_DIR = INFERENCE_ROOT / "receipts"
REQUESTS_DIR = INFERENCE_ROOT / "requests"
RESPONSES_DIR = INFERENCE_ROOT / "responses"
ERRORS_DIR = INFERENCE_ROOT / "errors"


def _is_hex64(s: str) -> bool:
    if not isinstance(s, str) or len(s) != 64:
        return False
    try:
        int(s, 16)
        return True
    except Exception:
        return False


def inference_replay(tool_input: Dict[str, Any]) -> Dict[str, Any]:
    if not isinstance(tool_input, dict):
        raise TypeError("tool_input must be dict")

    receipt_id = tool_input.get("receipt_id")
    if not isinstance(receipt_id, str) or not receipt_id.strip():
        raise ValueError("tool_input.receipt_id must be non-empty string")
    receipt_id = receipt_id.strip()

    receipt_path = RECEIPTS_DIR / f"{receipt_id}.json"
    if not receipt_path.exists():
        raise ValueError(f"replay_reject: receipt file missing: {receipt_path}")

    obj = json.loads(receipt_path.read_text(encoding="utf-8"))

    if obj.get("kind") != "inference.receipt":
        raise ValueError("replay_reject: invalid receipt kind")

    receipt_hash_stored = obj.get("receipt_hash")
    if not _is_hex64(receipt_hash_stored):
        raise ValueError("replay_reject: invalid stored receipt_hash")

    request_id = obj.get("request_id")
    result = obj.get("result")
    inputs_sha = obj.get("inputs_sha256")

    if not isinstance(request_id, str) or not request_id:
        raise ValueError("replay_reject: invalid request_id")
    if not isinstance(result, dict):
        raise ValueError("replay_reject: invalid result block")
    if not isinstance(inputs_sha, dict):
        raise ValueError("replay_reject: invalid inputs_sha256 block")

    result_kind = result.get("kind")
    result_id = result.get("artifact_id")

    if result_kind not in {"response", "error"}:
        raise ValueError("replay_reject: invalid result.kind")
    if not isinstance(result_id, str) or not result_id:
        raise ValueError("replay_reject: invalid result.artifact_id")

    request_path = REQUESTS_DIR / f"{request_id}.json"
    if not request_path.exists():
        raise ValueError("replay_reject: request file missing")

    if result_kind == "response":
        result_path = RESPONSES_DIR / f"{result_id}.json"
    else:
        result_path = ERRORS_DIR / f"{result_id}.json"

    if not result_path.exists():
        raise ValueError("replay_reject: result file missing")

    # Recompute file hashes
    request_sha_actual = sha256_file(request_path)
    result_sha_actual = sha256_file(result_path)

    if request_sha_actual != inputs_sha.get("request_sha256"):
        raise ValueError("replay_reject: request sha mismatch")

    if result_sha_actual != inputs_sha.get("result_sha256"):
        raise ValueError("replay_reject: result sha mismatch")

    # Recompute receipt hash deterministically (exclude receipt_hash)
    base = dict(obj)
    base.pop("receipt_hash", None)

    receipt_hash_recomputed = sha256_hex(canonical_dumps(base))

    if receipt_hash_recomputed != receipt_hash_stored:
        raise ValueError("replay_reject: receipt_hash mismatch")

    return {
        "status": "replay_ok",
        "receipt_id": receipt_id,
        "request_sha256": request_sha_actual,
        "result_sha256": result_sha_actual,
        "receipt_hash": receipt_hash_recomputed,
    }
