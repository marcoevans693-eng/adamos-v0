# Procedure: Phase 8 Step 1 proof - inference.request_emit creates request file + registry record + idempotency
from __future__ import annotations

import json
import sys
from pathlib import Path

# Ensure repo root is on sys.path so `import adam_os` works even without PYTHONPATH
REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT))

from adam_os.execution_core.executor import LocalExecutor  # noqa: E402


def main() -> None:
    e = LocalExecutor()

    created_at_utc = "2026-02-14T00:00:00Z"
    snapshot_hash = "a" * 64  # deterministic placeholder for proof

    tool_input = {
        "created_at_utc": created_at_utc,
        "snapshot_hash": snapshot_hash,
        "provider": "openai",
        "model": "gpt-4.1-mini",
        "system_prompt": "",
        "user_prompt": "hello",
        "temperature": 0.0,
        "max_tokens": 16,
        "provider_max_tokens_cap": 1024,
    }

    r1 = e.execute_tool("inference.request_emit", tool_input)
    assert r1["kind"] == "INFERENCE_REQUEST"
    p = Path(r1["request_path"])
    assert p.exists(), "request file not created"

    obj = json.loads(p.read_text(encoding="utf-8"))
    assert obj["kind"] == "inference.request"
    assert obj["created_at_utc"] == created_at_utc
    assert obj["snapshot_hash"] == snapshot_hash
    assert obj["provider"] == "openai"
    assert obj["model"] == "gpt-4.1-mini"
    assert obj["params"]["max_tokens"] == 16

    reg_path = Path(r1["registry_path"])
    assert reg_path.exists(), "registry not created"

    # Idempotency: re-run identical request; should return without errors and keep same artifact_id
    r2 = e.execute_tool("inference.request_emit", tool_input)
    assert r2["artifact_id"] == r1["artifact_id"]
    assert Path(r2["request_path"]).exists()

    # Basic registry presence: must contain artifact_id + kind
    txt = reg_path.read_text(encoding="utf-8")
    assert f"\"artifact_id\":\"{r1['artifact_id']}\"" in txt
    assert "\"kind\":\"INFERENCE_REQUEST\"" in txt

    print("phase8_step1_proof OK")


if __name__ == "__main__":
    main()
