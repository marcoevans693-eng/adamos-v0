# Procedure: Phase 9 Step 8 proof - AnthropicHTTPError maps to error_type=provider_http_error
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT))

from adam_os.execution_core.executor import LocalExecutor  # noqa: E402


def main() -> None:
    # Force an Anthropic HTTP failure deterministically by using a bogus key.
    os.environ["ANTHROPIC_API_KEY"] = "invalid-key-for-parity-proof"

    e = LocalExecutor()
    created_at_utc = "2026-02-16T00:00:00Z"
    snapshot_hash = "c" * 64

    # Must be allowlisted model so we reach execution.
    req_in = {
        "created_at_utc": created_at_utc,
        "snapshot_hash": snapshot_hash,
        "provider": "anthropic",
        "model": "claude-3-haiku",
        "system_prompt": "You are a deterministic test harness.",
        "user_prompt": "Say OK",
        "temperature": 0.0,
        "max_tokens": 16,
        "provider_max_tokens_cap": 256,
    }

    req_out = e.execute_tool("inference.request_emit", req_in)
    request_id = req_out["artifact_id"]

    exec_out = e.execute_tool("inference.execute", {"created_at_utc": created_at_utc, "request_id": request_id})

    if exec_out.get("ok") is not False:
        raise SystemExit(f"FAIL: expected error path, got ok={exec_out.get('ok')}")

    emitted_error = exec_out.get("emitted_error") or {}
    error_path = emitted_error.get("error_path")
    if not isinstance(error_path, str) or not error_path:
        raise SystemExit("FAIL: missing emitted_error.error_path")

    obj = json.loads(Path(error_path).read_text(encoding="utf-8"))
    et = obj.get("error_type")
    if et != "provider_http_error":
        raise SystemExit(f"FAIL: expected error_type=provider_http_error, got={et}")

    print(
        json.dumps(
            {
                "ok": True,
                "proof": "phase9_step8_anthropic_http_error_parity_proof",
                "request_id": request_id,
                "error_type": et,
            },
            indent=2,
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
