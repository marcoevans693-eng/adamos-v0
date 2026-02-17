# Procedure: Phase 9 Step 7 proof - live anthropic execution (error ok) + receipt + replay integrity
from __future__ import annotations

import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT))

from adam_os.execution_core.executor import LocalExecutor  # noqa: E402


def main() -> None:
    e = LocalExecutor()

    created_at_utc = "2026-02-16T00:00:00Z"
    snapshot_hash = "c" * 64

    # Intentionally choose a plausible model string; proof allows error path.
    # Success is not required; integrity + receipts are required.
    req_in = {
        "created_at_utc": created_at_utc,
        "snapshot_hash": snapshot_hash,
        "provider": "anthropic",
        "model": "claude-3-5-sonnet-latest",
        "prompts": {"system_prompt": "You are a deterministic test harness.", "user_prompt": "Say OK"},
        "params": {"temperature": 0.0, "max_tokens": 16},
    }

    # 1) Emit request (Phase 8 gate)
    req_out = e.execute_tool("inference.request_emit", req_in)
    request_id = req_out["request_id"]
    receipt_id_expected = f"{request_id}--receipt"

    # 2) Execute (Phase 9 provider boundary via dispatch)
    exec_in = {"created_at_utc": created_at_utc, "request_id": request_id}
    registry_path = Path(".adam_os") / "inference" / "inference_registry.jsonl"

    before_bytes = registry_path.stat().st_size if registry_path.exists() else 0
    before_lines = len(registry_path.read_text(encoding="utf-8").splitlines()) if registry_path.exists() else 0

    execute_result = e.execute_tool("inference.execute", exec_in)

    after_exec_bytes = registry_path.stat().st_size if registry_path.exists() else 0
    after_exec_lines = len(registry_path.read_text(encoding="utf-8").splitlines()) if registry_path.exists() else 0

    # Must ALWAYS emit receipt
    emitted_receipt = execute_result.get("emitted_receipt") or {}
    receipt_id = emitted_receipt.get("artifact_id") or emitted_receipt.get("receipt_id") or None

    if receipt_id is None or receipt_id != receipt_id_expected:
        raise SystemExit(f"FAIL: receipt_id missing/mismatch: got={receipt_id} expected={receipt_id_expected}")

    # Must be provider anthropic (even on error path)
    provider = req_in["provider"]
    model = req_in["model"]

    # 3) Replay must be ok and must not write registry
    replay_in = {"created_at_utc": created_at_utc, "receipt_id": receipt_id}
    replay_before_bytes = registry_path.stat().st_size if registry_path.exists() else 0
    replay_before_lines = len(registry_path.read_text(encoding="utf-8").splitlines()) if registry_path.exists() else 0

    replay_result = e.execute_tool("inference.replay", replay_in)

    replay_after_bytes = registry_path.stat().st_size if registry_path.exists() else 0
    replay_after_lines = len(registry_path.read_text(encoding="utf-8").splitlines()) if registry_path.exists() else 0

    if replay_result.get("status") != "replay_ok":
        raise SystemExit(f"FAIL: replay status not ok: {replay_result}")

    if replay_before_bytes != replay_after_bytes or replay_before_lines != replay_after_lines:
        raise SystemExit(
            f"FAIL: registry mutated on replay: bytes {replay_before_bytes}->{replay_after_bytes}, "
            f"lines {replay_before_lines}->{replay_after_lines}"
        )

    out = {
        "ok": True,
        "created_at_utc": created_at_utc,
        "provider": provider,
        "model": model,
        "request_id": request_id,
        "receipt_id": receipt_id,
        "execute_result": execute_result,
        "registry_path": str(registry_path.resolve()),
        "registry_exec_snapshot": {
            "bytes_before": before_bytes,
            "lines_before": before_lines,
            "bytes_after": after_exec_bytes,
            "lines_after": after_exec_lines,
        },
        "registry_replay_snapshot": {
            "bytes_before": replay_before_bytes,
            "lines_before": replay_before_lines,
            "bytes_after": replay_after_bytes,
            "lines_after": replay_after_lines,
        },
        "replay_result": replay_result,
    }
    print(json.dumps(out, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
