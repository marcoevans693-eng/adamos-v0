#!/usr/bin/env python3
"""
Phase 9 Sanity Runner (Troubleshoot Gate Closer)

Orchestration-only. No schema changes. No tool refactors.
- Derives prompts/settings from a known-good template request artifact.
- Emits a fresh request via inference.request_emit (contract-complete tool_input).
- Executes inference.execute on the fresh request_id.
- Verifies registry contains REQUEST + RESPONSE + RECEIPT for that request_id.
- Verifies receipt binds to RESPONSE (not ERROR).
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
from pathlib import Path
from datetime import datetime, timezone

HEX64_RE = re.compile(r"^[0-9a-f]{64}$")


def _die(msg: str, code: int = 2) -> None:
    print(f"RUNNER_FAIL: {msg}", file=sys.stderr)
    raise SystemExit(code)


def _read_json(path: Path) -> dict:
    if not path.exists():
        _die(f"missing file: {path}")
    return json.loads(path.read_text(encoding="utf-8"))


def _iso_utc_now_z() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _require_hex64(name: str, value: str) -> None:
    if not isinstance(value, str) or not HEX64_RE.match(value):
        _die(f"{name} must be 64-hex, got: {value!r}")


def _require_number(name: str, value) -> None:
    if not isinstance(value, (int, float)):
        _die(f"{name} must be a number, got: {type(value).__name__}={value!r}")


def _extract_request_id(emitted_req: dict) -> str:
    # Wrapper shape: {"ok": True, "request_id": "..."} (or request_hash)
    if isinstance(emitted_req.get("request_id"), str):
        return emitted_req["request_id"]
    if isinstance(emitted_req.get("request_hash"), str):
        return emitted_req["request_hash"]

    # Artifact shape: {"artifact_id": "<64hex>", "kind": "INFERENCE_REQUEST", ...}
    aid = emitted_req.get("artifact_id")
    if isinstance(aid, str) and HEX64_RE.match(aid):
        return aid

    _die(f"cannot extract request_id from request_emit output: {emitted_req!r}")
    return ""


def _is_request_emit_success(emitted_req: dict) -> bool:
    if emitted_req.get("ok") is True:
        return True
    if emitted_req.get("kind") == "INFERENCE_REQUEST" and isinstance(emitted_req.get("artifact_id"), str):
        return True
    return False


def _receipt_binds_to_response(receipt: dict, request_id: str) -> bool:
    # Newer shape observed:
    # {"kind":"inference.receipt", "result":{"artifact_id":"<req>--response","kind":"response"}, ...}
    res = receipt.get("result")
    if isinstance(res, dict):
        aid = res.get("artifact_id")
        if aid == f"{request_id}--response":
            return True
        if aid == f"{request_id}--error":
            return False

    # Older/alternative shape (if present)
    parents = receipt.get("parent_artifact_ids")
    if isinstance(parents, list):
        if f"{request_id}--response" in parents and f"{request_id}--error" not in parents:
            return True
        if f"{request_id}--error" in parents:
            return False

    return False


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument(
        "--template-request-id",
        default="a705a338f98da037c7bb9b4849b7aaa57211e5e107517119bddb429d4269f9eb",
        help="Template request id under .adam_os/inference/requests/ (known-good).",
    )
    ap.add_argument(
        "--created-at-utc",
        default=None,
        help="created_at_utc for NEW request. If omitted, uses current UTC (Z).",
    )
    ap.add_argument(
        "--verify-only",
        action="store_true",
        help="Emit request only; skip inference.execute + ledger checks.",
    )
    args = ap.parse_args()

    repo_root = Path.cwd()
    if not (repo_root / ".adam_os").exists():
        _die("run from repo root where .adam_os/ exists (cd /workspaces/adamos-v0)")

    created_at_utc = args.created_at_utc or _iso_utc_now_z()

    template_path = repo_root / ".adam_os" / "inference" / "requests" / f"{args.template_request_id}.json"
    tpl = _read_json(template_path)

    provider = tpl.get("provider")
    model = tpl.get("model")
    prompts = tpl.get("prompts") or {}
    system_prompt = prompts.get("system_prompt", "")
    user_prompt = prompts.get("user_prompt", "")
    params = tpl.get("params") or {}
    max_tokens = params.get("max_tokens")
    temperature = params.get("temperature")
    snapshot_hash = tpl.get("snapshot_hash")

    if provider != "openai":
        _die(f"template provider expected 'openai', got: {provider!r}")
    if not isinstance(model, str) or not model:
        _die(f"template model missing/invalid: {model!r}")

    _require_number("max_tokens", max_tokens)
    _require_number("temperature", temperature)

    if not isinstance(system_prompt, str) or not isinstance(user_prompt, str):
        _die("template prompts invalid (system_prompt/user_prompt must be strings)")
    if not isinstance(snapshot_hash, str):
        _die("template snapshot_hash missing/invalid")
    _require_hex64("snapshot_hash", snapshot_hash)

    try:
        from adam_os.execution_core.executor import LocalExecutor as E
    except Exception as e:
        _die(f"failed importing LocalExecutor: {e}")

    ex = E()

    tool_input = {
        "created_at_utc": created_at_utc,
        "provider": provider,
        "model": model,
        "max_tokens": max_tokens,
        "temperature": temperature,
        "system_prompt": system_prompt,
        "user_prompt": user_prompt,
        "snapshot_hash": snapshot_hash,
        "provider_max_tokens_cap": max_tokens,
        "provider_temperature_cap": temperature,
    }

    emitted_req = ex.execute_tool("inference.request_emit", tool_input)
    if not isinstance(emitted_req, dict) or not _is_request_emit_success(emitted_req):
        _die(f"inference.request_emit unexpected output: {emitted_req!r}")

    request_id = _extract_request_id(emitted_req)
    _require_hex64("new request_id", request_id)

    request_path = emitted_req.get("request_path")
    if not isinstance(request_path, str):
        request_path = str(repo_root / ".adam_os" / "inference" / "requests" / f"{request_id}.json")

    print(f"NEW_REQUEST_ID: {request_id}")
    print(f"NEW_REQUEST_PATH: {request_path}")

    if args.verify_only:
        print("VERIFY_ONLY: true (skipping inference.execute)")
        return 0

    if not os.environ.get("OPENAI_API_KEY"):
        _die("OPENAI_API_KEY is missing in this shell (export it before running runner)")

    exec_out = ex.execute_tool("inference.execute", {"created_at_utc": created_at_utc, "request_id": request_id})
    if not isinstance(exec_out, dict) or not exec_out.get("ok"):
        _die(f"inference.execute did not return ok dict: {exec_out!r}")

    registry_path = repo_root / ".adam_os" / "inference" / "inference_registry.jsonl"
    if not registry_path.exists():
        _die(f"missing registry: {registry_path}")

    lines = registry_path.read_text(encoding="utf-8").splitlines()
    entries = []
    for ln in lines:
        try:
            obj = json.loads(ln)
        except Exception:
            continue
        if obj.get("artifact_id", "").startswith(request_id):
            entries.append(obj)

    kinds = [e.get("kind") for e in entries]
    if "INFERENCE_REQUEST" not in kinds:
        _die(f"registry missing INFERENCE_REQUEST for {request_id}")
    if "INFERENCE_RESPONSE" not in kinds:
        _die(f"registry missing INFERENCE_RESPONSE for {request_id}")
    if "INFERENCE_RECEIPT" not in kinds:
        _die(f"registry missing INFERENCE_RECEIPT for {request_id}")
    if "INFERENCE_ERROR" in kinds:
        _die(f"registry contains INFERENCE_ERROR for {request_id} (fresh-run stability failed)")

    receipt_path = repo_root / ".adam_os" / "inference" / "receipts" / f"{request_id}--receipt.json"
    receipt = _read_json(receipt_path)

    if not _receipt_binds_to_response(receipt, request_id):
        _die(f"receipt does not bind to response for {request_id}")

    print("SANITY_RESULT: PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
