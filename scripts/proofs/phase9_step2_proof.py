# Procedure: Phase 9 Step 2 proof - inference.execute MUST emit receipt (success OR error)
from __future__ import annotations

import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT))

from adam_os.execution_core.executor import LocalExecutor  # noqa: E402


INFERENCE_ROOT = Path(".adam_os") / "inference"
REGISTRY_PATH = INFERENCE_ROOT / "inference_registry.jsonl"


def _registry_has(artifact_id: str, kind: str) -> bool:
    if not REGISTRY_PATH.exists():
        return False
    with REGISTRY_PATH.open("r", encoding="utf-8") as f:
        for line in f:
            try:
                obj = json.loads(line)
            except Exception:
                continue
            if obj.get("artifact_id") == artifact_id and obj.get("kind") == kind:
                return True
    return False


def main() -> None:
    e = LocalExecutor()

    created_at_utc = "2026-02-16T00:00:00Z"
    snapshot_hash = "a" * 64

    req_out = e.execute_tool(
        "inference.request_emit",
        {
            "created_at_utc": created_at_utc,
            "snapshot_hash": snapshot_hash,
            "provider": "openai",
            "model": "gpt-4.1-mini",
            "temperature": 0.0,
            "max_tokens": 16,
            "provider_max_tokens_cap": 4096,
            "system_prompt": "",
            "user_prompt": "ping",
        },
    )

    request_id = req_out["artifact_id"]

    ex_out = e.execute_tool(
        "inference.execute",
        {
            "created_at_utc": created_at_utc,
            "request_id": request_id,
        },
    )

    response_id = f"{request_id}--response"
    error_id = f"{request_id}--error"
    receipt_id = f"{request_id}--receipt"

    has_response = _registry_has(response_id, "INFERENCE_RESPONSE")
    has_error = _registry_has(error_id, "INFERENCE_ERROR")
    has_receipt = _registry_has(receipt_id, "INFERENCE_RECEIPT")

    if not (has_response or has_error):
        raise AssertionError("missing both INFERENCE_RESPONSE and INFERENCE_ERROR")

    if not has_receipt:
        raise AssertionError("missing INFERENCE_RECEIPT")

    receipt_path = INFERENCE_ROOT / "receipts" / f"{receipt_id}.json"
    if not receipt_path.exists():
        raise AssertionError(f"missing receipt artifact file: {receipt_path}")

    print(json.dumps({
        "ok": True,
        "request_id": request_id,
        "execute_ok": bool(ex_out.get("ok")),
        "path": "response" if has_response else "error"
    }, sort_keys=True))


if __name__ == "__main__":
    main()
