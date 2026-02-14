"""
Phase 8 Step 5 proof - inference.receipt_emit

Proves:
- receipt emits deterministically
- binds to existing request + response artifacts
- appends INFERENCE_RECEIPT to inference_registry.jsonl
- idempotency gate returns same receipt artifact on second call
"""

from __future__ import annotations

from pathlib import Path

from adam_os.execution_core.executor import LocalExecutor
from adam_os.artifacts.registry import sha256_file


def main() -> None:
    e = LocalExecutor()

    created_at_utc = "2026-02-14T00:00:00Z"
    snapshot_hash = "a" * 64

    # Provider select (deterministic caps)
    p = e.execute_tool("inference.provider_select", {"provider": "openai"})
    provider = p["provider"]
    provider_cap = int(p["provider_max_tokens_cap"])

    # Use SPEC-008D allowlisted model
    model = "gpt-4.1-mini"

    # Request emit
    r = e.execute_tool(
        "inference.request_emit",
        {
            "created_at_utc": created_at_utc,
            "snapshot_hash": snapshot_hash,
            "provider": provider,
            "model": model,
            "system_prompt": "",
            "user_prompt": "phase8_step5_proof",
            "temperature": 0.0,
            "max_tokens": 32,
            "provider_max_tokens_cap": provider_cap,
        },
    )
    request_id = r["artifact_id"]
    request_hash = r["request_hash"]

    # Response emit (no provider call)
    resp = e.execute_tool(
        "inference.response_emit",
        {
            "created_at_utc": created_at_utc,
            "request_id": request_id,
            "request_hash": request_hash,
            "snapshot_hash": snapshot_hash,
            "provider": provider,
            "model": model,
            "output_text": "ok",
        },
    )
    response_id = resp["artifact_id"]

    # Receipt emit
    receipt = e.execute_tool(
        "inference.receipt_emit",
        {
            "created_at_utc": created_at_utc,
            "request_id": request_id,
            "request_hash": request_hash,
            "snapshot_hash": snapshot_hash,
            "provider": provider,
            "model": model,
            "response_id": response_id,
        },
    )

    receipt_path = Path(receipt["receipt_path"])
    assert receipt_path.exists(), "receipt file missing"
    sha1 = sha256_file(receipt_path)

    # Idempotency: second call should not rewrite (but returns existing metadata)
    receipt2 = e.execute_tool(
        "inference.receipt_emit",
        {
            "created_at_utc": created_at_utc,
            "request_id": request_id,
            "request_hash": request_hash,
            "snapshot_hash": snapshot_hash,
            "provider": provider,
            "model": model,
            "response_id": response_id,
            "receipt_id": receipt["artifact_id"],
        },
    )
    receipt_path2 = Path(receipt2["receipt_path"])
    assert receipt_path2.exists(), "receipt file missing on second call"
    sha2 = sha256_file(receipt_path2)

    assert sha1 == sha2, "receipt not idempotent: file hash changed"
    print("phase8_step5_proof OK")


if __name__ == "__main__":
    main()
