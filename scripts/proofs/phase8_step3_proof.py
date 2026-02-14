# Procedure: Phase 8 Step 3 proof - response/error artifacts are emitted + registry append + idempotency
from __future__ import annotations

import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT))

from adam_os.execution_core.executor import LocalExecutor  # noqa: E402


def main() -> None:
    e = LocalExecutor()

    created_at_utc = "2026-02-14T00:00:00Z"
    snapshot_hash = "c" * 64

    # 1) Create request
    req_in = {
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
    rreq = e.execute_tool("inference.request_emit", req_in)
    req_id = rreq["artifact_id"]

    req_obj = json.loads(Path(rreq["request_path"]).read_text(encoding="utf-8"))
    request_hash = req_obj["request_hash"]

    # 2) Emit response
    resp_in = {
        "created_at_utc": created_at_utc,
        "request_id": req_id,
        "request_hash": request_hash,
        "snapshot_hash": snapshot_hash,
        "provider": "openai",
        "model": "gpt-4.1-mini",
        "output_text": "stub response text",
    }
    r1 = e.execute_tool("inference.response_emit", resp_in)
    assert r1["kind"] == "INFERENCE_RESPONSE"
    rp = Path(r1["response_path"])
    assert rp.exists()

    robj = json.loads(rp.read_text(encoding="utf-8"))
    assert robj["kind"] == "inference.response"
    assert robj["request_id"] == req_id
    assert robj["request_hash"] == request_hash

    # Idempotency
    r2 = e.execute_tool("inference.response_emit", resp_in)
    assert r2["artifact_id"] == r1["artifact_id"]

    # 3) Emit error
    err_in = {
        "created_at_utc": created_at_utc,
        "request_id": req_id,
        "request_hash": request_hash,
        "snapshot_hash": snapshot_hash,
        "provider": "openai",
        "model": "gpt-4.1-mini",
        "error_type": "PROVIDER_TIMEOUT",
        "message": "timeout",
        "details": "stub details",
    }
    e1 = e.execute_tool("inference.error_emit", err_in)
    assert e1["kind"] == "INFERENCE_ERROR"
    ep = Path(e1["error_path"])
    assert ep.exists()

    eobj = json.loads(ep.read_text(encoding="utf-8"))
    assert eobj["kind"] == "inference.error"
    assert eobj["request_id"] == req_id
    assert eobj["request_hash"] == request_hash

    # Idempotency
    e2 = e.execute_tool("inference.error_emit", err_in)
    assert e2["artifact_id"] == e1["artifact_id"]

    # 4) Registry contains both entries
    reg = Path(r1["registry_path"])
    txt = reg.read_text(encoding="utf-8")
    assert f"\"artifact_id\":\"{r1['artifact_id']}\"" in txt
    assert "\"kind\":\"INFERENCE_RESPONSE\"" in txt
    assert f"\"artifact_id\":\"{e1['artifact_id']}\"" in txt
    assert "\"kind\":\"INFERENCE_ERROR\"" in txt

    print("phase8_step3_proof OK")


if __name__ == "__main__":
    main()
