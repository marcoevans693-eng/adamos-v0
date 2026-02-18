"""Phase 10 Observability Step 1 Proof

Validates:
- Append writes exactly one JSONL line
- SHA returned matches sha256 of exact appended line bytes (including trailing \n)
- File is append-only by construction (we only open in 'ab')
"""

from __future__ import annotations

import hashlib
from pathlib import Path

from adam_os.tools.engineering_log_append import append_engineering_event, DEFAULT_ACTIVITY_LOG_PATH


def main() -> None:
    log_path = Path(DEFAULT_ACTIVITY_LOG_PATH)
    log_path.parent.mkdir(parents=True, exist_ok=True)
    log_path.touch(exist_ok=True)

    before = log_path.read_bytes()
    before_lines = before.splitlines()

    event = {
        "created_at_utc": "2026-02-18T00:00:00Z",
        "event_type": "tool_execute",
        "tool_name": "engineering_log_append",
        "status": "success",
        "note": "phase10_observability_step1_proof",
    }

    sha = append_engineering_event(event, log_path=log_path)

    after = log_path.read_bytes()
    after_lines = after.splitlines()

    # exactly one additional line
    assert len(after_lines) == len(before_lines) + 1, (len(before_lines), len(after_lines))

    # compute sha256 over the exact appended bytes (line + trailing \n)
    appended_line = after[len(before):]
    assert appended_line.endswith(b"\n"), "appended bytes must end with newline"
    expected_sha = hashlib.sha256(appended_line).hexdigest()
    assert sha == expected_sha, (sha, expected_sha)

    print("OK: appended 1 line")
    print(f"LOG_PATH: {log_path}")
    print(f"APPENDED_SHA256: {sha}")
    print(f"APPENDED_BYTES: {len(appended_line)}")


if __name__ == "__main__":
    main()
