# Procedure: Proof — inference.response_emit emits engineering activity events (fresh + idempotent)
from __future__ import annotations

import json
from pathlib import Path

from adam_os.tools.inference_response_emit import inference_response_emit

ENGINEERING_LOG = Path(".adam_os") / "engineering" / "activity_log.jsonl"
RESPONSES_DIR = Path(".adam_os") / "inference" / "responses"


def _lines(path: Path) -> list[str]:
    if not path.exists():
        return []
    return path.read_text(encoding="utf-8").splitlines()


def _last_event() -> dict | None:
    ls = _lines(ENGINEERING_LOG)
    if not ls:
        return None
    return json.loads(ls[-1])


def main() -> None:
    request_id = "e" * 64
    response_id = f"{request_id}--response"
    resp_path = RESPONSES_DIR / f"{response_id}.json"

    # Force a fresh emit (response file removed, registry may still contain old entries but idempotency gate checks file+registry)
    if resp_path.exists():
        resp_path.unlink()

    before_lines = _lines(ENGINEERING_LOG)
    before_n = len(before_lines)

    out = inference_response_emit(
        {
            "created_at_utc": "2026-02-17T00:00:10Z",
            "request_id": request_id,
            "request_hash": "f" * 64,
            "snapshot_hash": "a" * 64,
            "provider": "openai",
            "model": "gpt-4o-mini",
            "output_text": "pong",
            "response_id": response_id,
        }
    )
    assert out["artifact_id"] == response_id

    after_lines = _lines(ENGINEERING_LOG)
    assert len(after_lines) == before_n + 1

    evt1 = _last_event()
    assert evt1 is not None
    assert evt1.get("event_type") == "tool_execute"
    assert evt1.get("tool_name") == "inference.response_emit"
    assert evt1.get("request_id") == request_id
    assert evt1.get("artifact_id") == response_id
    assert evt1.get("status") == "success"
    assert evt1.get("kind") == "INFERENCE_RESPONSE"
    assert evt1.get("idempotent") is False

    # Second run should be idempotent and append another event with idempotent=True
    before2_n = len(_lines(ENGINEERING_LOG))
    out2 = inference_response_emit(
        {
            "created_at_utc": "2026-02-17T00:00:11Z",
            "request_id": request_id,
            "request_hash": "f" * 64,
            "snapshot_hash": "a" * 64,
            "provider": "openai",
            "model": "gpt-4o-mini",
            "output_text": "pong",
            "response_id": response_id,
        }
    )
    assert out2["artifact_id"] == response_id

    after2_lines = _lines(ENGINEERING_LOG)
    assert len(after2_lines) == before2_n + 1

    evt2 = _last_event()
    assert evt2 is not None
    assert evt2.get("event_type") == "tool_execute"
    assert evt2.get("tool_name") == "inference.response_emit"
    assert evt2.get("request_id") == request_id
    assert evt2.get("artifact_id") == response_id
    assert evt2.get("status") == "success"
    assert evt2.get("kind") == "INFERENCE_RESPONSE"
    assert evt2.get("idempotent") is True

    print("phase10_observability_step3_response_emit_proof OK")


if __name__ == "__main__":
    main()
