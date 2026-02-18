# Procedure: Proof — Phase10 Step3 Part4 (artifact.ingest emits engineering activity events)
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List

from adam_os.tools.artifact_ingest import artifact_ingest

ACT_LOG = Path(".adam_os/engineering/activity_log.jsonl")


def _read_jsonl(path: Path) -> List[Dict[str, Any]]:
    if not path.exists():
        return []
    out: List[Dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            out.append(json.loads(line))
    return out


def _tail_tool_events(events: List[Dict[str, Any]], tool_name: str) -> List[Dict[str, Any]]:
    return [e for e in events if e.get("event_type") == "tool_execute" and e.get("tool_name") == tool_name]


def main() -> None:
    before = _read_jsonl(ACT_LOG)
    before_n = len(before)

    # 1) Success
    r1 = artifact_ingest(
        {
            "created_at_utc": "2026-02-17T11:00:00Z",
            "content": "hello world\n",
            "media_type": "text/plain",
        }
    )
    assert r1["kind"] == "RAW"
    assert isinstance(r1.get("artifact_id"), str) and r1["artifact_id"]

    mid = _read_jsonl(ACT_LOG)
    assert len(mid) == before_n + 1, "expected exactly 1 new engineering event after success call"

    tool_events_mid = _tail_tool_events(mid[before_n:], "artifact.ingest")
    assert len(tool_events_mid) == 1
    assert tool_events_mid[0]["status"] == "success"
    assert tool_events_mid[0].get("artifact_id") == r1["artifact_id"]

    # 2) Error
    try:
        artifact_ingest(
            {
                "created_at_utc": "2026-02-17T11:00:01Z",
                "content": "",  # invalid
            }
        )
        raise AssertionError("expected error, but call succeeded")
    except Exception:
        pass

    after = _read_jsonl(ACT_LOG)
    assert len(after) == before_n + 2, "expected exactly 1 additional engineering event after error case"

    tool_events_after = _tail_tool_events(after[before_n:], "artifact.ingest")
    assert len(tool_events_after) == 2
    assert tool_events_after[1]["status"] == "error"
    assert tool_events_after[1].get("exception_type") is not None
    assert tool_events_after[1].get("exception_message") is not None

    print(
        json.dumps(
            {
                "ok": True,
                "tool": "artifact.ingest",
                "new_events_added": 2,
                "statuses": [tool_events_after[0]["status"], tool_events_after[1]["status"]],
            },
            indent=2,
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
