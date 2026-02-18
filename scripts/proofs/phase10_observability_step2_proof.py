"""Phase 10 Observability Step 2 Proof

Validates:
- log_tool_execution emits standardized fields
- Appends exactly one JSONL line per call
- Returned sha matches sha256 of exact appended bytes (including trailing \n)
"""

from __future__ import annotations

import hashlib
from pathlib import Path

from adam_os.engineering.activity_events import log_tool_execution
from adam_os.tools.engineering_log_append import DEFAULT_ACTIVITY_LOG_PATH


def main() -> None:
    log_path = Path(DEFAULT_ACTIVITY_LOG_PATH)
    log_path.parent.mkdir(parents=True, exist_ok=True)
    log_path.touch(exist_ok=True)

    before = log_path.read_bytes()
    before_lines = before.splitlines()

    sha = log_tool_execution(
        created_at_utc="2026-02-18T00:00:00Z",
        tool_name="phase10_observability_step2_proof",
        status="success",
        request_id="req_dummy",
        extra={"note": "step2"},
    )

    after = log_path.read_bytes()
    after_lines = after.splitlines()

    # exactly one additional line
    assert len(after_lines) == len(before_lines) + 1, (len(before_lines), len(after_lines))

    appended = after[len(before):]
    assert appended.endswith(b"\n"), "appended bytes must end with newline"

    expected_sha = hashlib.sha256(appended).hexdigest()
    assert sha == expected_sha, (sha, expected_sha)

    line = appended.decode("utf-8")

    # minimal content check (JSONL contains these substrings)
    assert '"event_type":"tool_execute"' in line
    assert '"tool_name":"phase10_observability_step2_proof"' in line
    assert '"status":"success"' in line
    assert '"request_id":"req_dummy"' in line
    assert '"note":"step2"' in line

    print("OK: step2 wrapper appended 1 line")
    print(f"LOG_PATH: {log_path}")
    print(f"APPENDED_SHA256: {sha}")
    print(f"APPENDED_BYTES: {len(appended)}")


if __name__ == "__main__":
    main()
