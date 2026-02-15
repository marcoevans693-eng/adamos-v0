# Procedure: Phase 8 Step 7 proof - Durability Matrix (success + policy rejects + integrity/tamper)
from __future__ import annotations

import json
import shutil
import sys
from pathlib import Path

# Ensure repo root is on sys.path so `import adam_os` works even without PYTHONPATH
REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT))

from adam_os.execution_core.executor import LocalExecutor  # noqa: E402


def must_fail(fn, contains: str) -> None:
    try:
        fn()
        raise AssertionError("expected failure, but succeeded")
    except Exception as ex:
        msg = str(ex)
        assert contains in msg, f"expected '{contains}' in error, got: {msg}"


def _read_request_hash(request_path: Path) -> str:
    obj = json.loads(request_path.read_text(encoding="utf-8"))
    rh = obj.get("request_hash")
    assert isinstance(rh, str) and len(rh) == 64
    return rh


def main() -> None:
    e = LocalExecutor()

    created_at_utc = "2026-02-14T00:00:00Z"
    snapshot_hash = "d" * 64

    # --- Provider select (deterministic) ---
    p = e.execute_tool("inference.provider_select", {"provider": "openai"})
    provider = p["provider"]
    provider_cap = int(p["provider_max_tokens_cap"])

    model_ok = "gpt-4.1-mini"

    # =========================================================================
    # A) Success path cycle:
    # provider_select -> request_emit -> response_emit -> receipt_emit -> replay (OK)
    # =========================================================================
    req_in = {
        "created_at_utc": created_at_utc,
        "snapshot_hash": snapshot_hash,
        "provider": provider,
        "model": model_ok,
        "system_prompt": "",
        "user_prompt": "phase8_step7_matrix_success",
        "temperature": 0.0,
        "max_tokens": 32,
        "provider_max_tokens_cap": provider_cap,
    }
    rreq = e.execute_tool("inference.request_emit", req_in)
    request_id = rreq["artifact_id"]
    request_path = Path(rreq["request_path"])
    request_hash = _read_request_hash(request_path)

    rresp = e.execute_tool(
        "inference.response_emit",
        {
            "created_at_utc": created_at_utc,
            "request_id": request_id,
            "request_hash": request_hash,
            "snapshot_hash": snapshot_hash,
            "provider": provider,
            "model": model_ok,
            "output_text": "ok",
        },
    )
    response_id = rresp["artifact_id"]

    rreceipt = e.execute_tool(
        "inference.receipt_emit",
        {
            "created_at_utc": created_at_utc,
            "request_id": request_id,
            "request_hash": request_hash,
            "snapshot_hash": snapshot_hash,
            "provider": provider,
            "model": model_ok,
            "response_id": response_id,
        },
    )
    receipt_id = rreceipt["artifact_id"]

    rreplay = e.execute_tool("inference.replay", {"receipt_id": receipt_id})
    assert rreplay["status"] == "replay_ok"

    # =========================================================================
    # B) Policy gate rejection cycles (fail-closed at request_emit)
    # - non-allowlisted model
    # - max_tokens > provider_cap
    # =========================================================================
    bad_model = dict(req_in)
    bad_model["user_prompt"] = "phase8_step7_bad_model"
    bad_model["model"] = "gpt-4o-mini"  # known rejected in Step 2 proof
    must_fail(lambda: e.execute_tool("inference.request_emit", bad_model), "model not allowlisted")

    bad_tokens = dict(req_in)
    bad_tokens["user_prompt"] = "phase8_step7_bad_tokens"
    bad_tokens["max_tokens"] = provider_cap + 1
    must_fail(lambda: e.execute_tool("inference.request_emit", bad_tokens), "exceeds provider hard cap")

    # =========================================================================
    # C1) Integrity/tamper cycle: tamper receipt file then replay must fail
    # (No sed; rewrite via json load/dump)
    # =========================================================================
    receipt_path = Path(".adam_os") / "inference" / "receipts" / f"{receipt_id}.json"
    assert receipt_path.exists(), "expected receipt file for tamper test"

    original_receipt_txt = receipt_path.read_text(encoding="utf-8")
    obj = json.loads(original_receipt_txt)
    obj["provider"] = "tampered-provider"
    receipt_path.write_text(
        json.dumps(obj, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n",
        encoding="utf-8",
    )
    must_fail(lambda: e.execute_tool("inference.replay", {"receipt_id": receipt_id}), "replay_reject")

    # Restore receipt so later tests aren't poisoned
    receipt_path.write_text(original_receipt_txt, encoding="utf-8")
    rreplay2 = e.execute_tool("inference.replay", {"receipt_id": receipt_id})
    assert rreplay2["status"] == "replay_ok"

    # =========================================================================
    # C2) Missing referenced artifact file then receipt_emit or replay must fail
    # We test BOTH:
    # - receipt_emit fails closed if referenced result file is missing
    # - replay fails closed if referenced request/result file is missing
    # =========================================================================

    # --- C2a: receipt_emit fails if response file missing ---
    req2_in = dict(req_in)
    req2_in["user_prompt"] = "phase8_step7_missing_response_receipt_emit"
    rreq2 = e.execute_tool("inference.request_emit", req2_in)
    request2_id = rreq2["artifact_id"]
    request2_hash = _read_request_hash(Path(rreq2["request_path"]))

    resp2 = e.execute_tool(
        "inference.response_emit",
        {
            "created_at_utc": created_at_utc,
            "request_id": request2_id,
            "request_hash": request2_hash,
            "snapshot_hash": snapshot_hash,
            "provider": provider,
            "model": model_ok,
            "output_text": "ok2",
        },
    )
    response2_id = resp2["artifact_id"]
    response2_path = Path(".adam_os") / "inference" / "responses" / f"{response2_id}.json"
    assert response2_path.exists()

    # Remove response file (fail-closed), then restore afterward
    backup_resp = response2_path.with_suffix(".json.bak_step7")
    shutil.copy2(response2_path, backup_resp)
    response2_path.unlink()

    must_fail(
        lambda: e.execute_tool(
            "inference.receipt_emit",
            {
                "created_at_utc": created_at_utc,
                "request_id": request2_id,
                "request_hash": request2_hash,
                "snapshot_hash": snapshot_hash,
                "provider": provider,
                "model": model_ok,
                "response_id": response2_id,
            },
        ),
        "missing response artifact file",
    )

    # restore response file
    shutil.move(str(backup_resp), str(response2_path))

    # --- C2b: replay fails if referenced result file missing ---
    # Create fresh cycle so we don't depend on restored artifacts above
    req3_in = dict(req_in)
    req3_in["user_prompt"] = "phase8_step7_missing_result_replay"
    rreq3 = e.execute_tool("inference.request_emit", req3_in)
    request3_id = rreq3["artifact_id"]
    request3_hash = _read_request_hash(Path(rreq3["request_path"]))

    resp3 = e.execute_tool(
        "inference.response_emit",
        {
            "created_at_utc": created_at_utc,
            "request_id": request3_id,
            "request_hash": request3_hash,
            "snapshot_hash": snapshot_hash,
            "provider": provider,
            "model": model_ok,
            "output_text": "ok3",
        },
    )
    response3_id = resp3["artifact_id"]

    receipt3 = e.execute_tool(
        "inference.receipt_emit",
        {
            "created_at_utc": created_at_utc,
            "request_id": request3_id,
            "request_hash": request3_hash,
            "snapshot_hash": snapshot_hash,
            "provider": provider,
            "model": model_ok,
            "response_id": response3_id,
        },
    )
    receipt3_id = receipt3["artifact_id"]

    response3_path = Path(".adam_os") / "inference" / "responses" / f"{response3_id}.json"
    assert response3_path.exists()

    backup_resp3 = response3_path.with_suffix(".json.bak_step7")
    shutil.copy2(response3_path, backup_resp3)
    response3_path.unlink()

    must_fail(lambda: e.execute_tool("inference.replay", {"receipt_id": receipt3_id}), "result file missing")

    # restore response3 file so repo state isn't left broken
    shutil.move(str(backup_resp3), str(response3_path))

    # =========================================================================
    print("phase8_step7_proof OK")


if __name__ == "__main__":
    main()
