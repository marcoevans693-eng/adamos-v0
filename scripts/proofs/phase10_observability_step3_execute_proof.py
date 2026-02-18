# Procedure: Proof — inference.execute emits engineering activity events for success + error without touching Phase 9 contracts
from __future__ import annotations

import json
from pathlib import Path

from adam_os.tools import inference_execute as ie
from adam_os.providers.openai_responses import OpenAIHTTPError

ENGINEERING_LOG = Path(".adam_os") / "engineering" / "activity_log.jsonl"
REQUESTS_DIR = Path(".adam_os") / "inference" / "requests"


def _read_last_event() -> dict | None:
    if not ENGINEERING_LOG.exists():
        return None
    lines = ENGINEERING_LOG.read_text(encoding="utf-8").splitlines()
    if not lines:
        return None
    return json.loads(lines[-1])


def _write_request(request_id: str, provider: str) -> None:
    REQUESTS_DIR.mkdir(parents=True, exist_ok=True)
    req_path = REQUESTS_DIR / f"{request_id}.json"

    obj = {
        "kind": "inference.request",
        "created_at_utc": "2026-02-17T00:00:01Z",
        "provider": provider,
        "model": "gpt-4o-mini",
        "snapshot_hash": "b" * 64,
        "request_hash": "c" * 64,
        "params": {"temperature": 1.0, "max_tokens": 16},
        "prompts": {"system_prompt": "", "user_prompt": "ping"},
    }

    req_path.write_text(json.dumps(obj, sort_keys=True), encoding="utf-8")


class _FakeDispatchOK:
    def __init__(self) -> None:
        self.provider = "openai"
        self.model = "gpt-4o-mini"
        self.output_text = "pong"
        self.provider_response_id = "prov-123"


def main() -> None:
    before = _read_last_event()

    # SUCCESS PATH (monkeypatch dispatch_text)
    request_id_ok = "a" * 64
    _write_request(request_id_ok, provider="openai")

    orig_dispatch = ie.dispatch_text
    try:
        ie.dispatch_text = lambda **kwargs: _FakeDispatchOK()  # type: ignore[assignment]
        out = ie.inference_execute({"created_at_utc": "2026-02-17T00:00:02Z", "request_id": request_id_ok})
        assert out.get("ok") is True
    finally:
        ie.dispatch_text = orig_dispatch  # type: ignore[assignment]

    evt1 = _read_last_event()
    assert evt1 is not None
    assert evt1.get("event_type") == "tool_execute"
    assert evt1.get("tool_name") == "inference.execute"
    assert evt1.get("request_id") == request_id_ok
    assert evt1.get("status") == "success"
    assert evt1.get("kind") == "INFERENCE_RESPONSE"

    # ERROR PATH (monkeypatch dispatch_text to raise OpenAIHTTPError)
    request_id_err = "d" * 64
    _write_request(request_id_err, provider="openai")

    def _boom(**kwargs):
        raise OpenAIHTTPError("test_openai_http_error")

    orig_dispatch = ie.dispatch_text
    try:
        ie.dispatch_text = _boom  # type: ignore[assignment]
        out2 = ie.inference_execute({"created_at_utc": "2026-02-17T00:00:03Z", "request_id": request_id_err})
        assert out2.get("ok") is False
    finally:
        ie.dispatch_text = orig_dispatch  # type: ignore[assignment]

    evt2 = _read_last_event()
    assert evt2 is not None
    assert evt2.get("event_type") == "tool_execute"
    assert evt2.get("tool_name") == "inference.execute"
    assert evt2.get("request_id") == request_id_err
    assert evt2.get("status") == "error"
    assert evt2.get("kind") == "INFERENCE_ERROR"

    # sanity: ensure we actually appended (not a no-op)
    assert evt2 != before

    print("phase10_observability_step3_execute_proof OK")


if __name__ == "__main__":
    main()
