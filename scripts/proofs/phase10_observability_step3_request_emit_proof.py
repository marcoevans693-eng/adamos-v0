from __future__ import annotations

import hashlib
import subprocess
from pathlib import Path

from adam_os.tools.inference_request_emit import inference_request_emit
from adam_os.tools.engineering_log_append import DEFAULT_ACTIVITY_LOG_PATH


def _snapshot_hash64() -> str:
    head = subprocess.check_output(["git", "rev-parse", "HEAD"]).decode().strip()
    return hashlib.sha256(head.encode("utf-8")).hexdigest()


def main() -> None:
    log_path = Path(DEFAULT_ACTIVITY_LOG_PATH)
    log_path.parent.mkdir(parents=True, exist_ok=True)
    log_path.touch(exist_ok=True)

    before_lines = log_path.read_text(encoding="utf-8").splitlines()
    snap = _snapshot_hash64()

    tool_input = {
        "created_at_utc": "2026-02-18T00:00:00Z",
        "snapshot_hash": snap,
        "provider": "openai",
        "model": "gpt-4.1-mini",
        "input": [
            {"role": "system", "content": "You are a deterministic test system."},
            {"role": "user", "content": "Return the string OK."},
        ],
        "temperature": 0.0,
        "max_output_tokens": 16,
    }

    out = inference_request_emit(tool_input)

    after_lines = log_path.read_text(encoding="utf-8").splitlines()
    assert len(after_lines) == len(before_lines) + 1, (len(before_lines), len(after_lines))
    last = after_lines[-1]

    assert "\"event_type\":\"tool_execute\"" in last
    assert "\"tool_name\":\"inference.request_emit\"" in last
    assert "\"status\":\"success\"" in last
    assert f"\"request_id\":\"{out[\"artifact_id\"]}\"" in last

    print("OK: request_emit produced request + logged tool_execute")
    print("REQUEST_ID:", out["artifact_id"])


if __name__ == "__main__":
    main()
