# Procedure: Phase 8 Step 2 proof - Policy Gate rejects invalid requests before artifact write
from __future__ import annotations

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT))

from adam_os.execution_core.executor import LocalExecutor  # noqa: E402


def must_fail(e: LocalExecutor, tool_input: dict, contains: str) -> None:
    try:
        e.execute_tool("inference.request_emit", tool_input)
        raise AssertionError("expected failure, but tool succeeded")
    except Exception as ex:
        msg = str(ex)
        assert contains in msg, f"expected '{contains}' in error, got: {msg}"


def main() -> None:
    e = LocalExecutor()

    base = {
        "created_at_utc": "2026-02-14T00:00:00Z",
        "snapshot_hash": "b" * 64,
        "provider": "openai",
        "model": "gpt-4.1-mini",
        "system_prompt": "",
        "user_prompt": "hello",
        "temperature": 0.0,
        "max_tokens": 16,
        "provider_max_tokens_cap": 1024,
    }

    # PASS baseline (should not raise)
    r = e.execute_tool("inference.request_emit", dict(base))
    assert r["kind"] == "INFERENCE_REQUEST"

    # FAIL: model not allowlisted
    bad_model = dict(base)
    bad_model["model"] = "gpt-4o-mini"
    must_fail(e, bad_model, "model not allowlisted")

    # FAIL: temperature out of bounds
    bad_temp = dict(base)
    bad_temp["temperature"] = 1.5
    must_fail(e, bad_temp, "temperature out of bounds")

    # FAIL: max_tokens exceeds cap
    bad_tokens = dict(base)
    bad_tokens["max_tokens"] = 2048
    must_fail(e, bad_tokens, "exceeds provider hard cap")

    # FAIL: missing cap injection
    bad_cap = dict(base)
    del bad_cap["provider_max_tokens_cap"]
    must_fail(e, bad_cap, "provider_max_tokens_cap")

    print("phase8_step2_proof OK")


if __name__ == "__main__":
    main()
