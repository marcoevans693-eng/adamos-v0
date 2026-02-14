"""
adam_os.inference.contracts

Phase 8 contract helpers.

This module defines strict builders/validators for inference artifacts.
Step 1 implemented inference.request only (no provider execution).
Step 2 adds Policy Gate enforcement (SPEC-008D).
"""

from __future__ import annotations

from typing import Any, Dict

from adam_os.memory.canonical import canonical_dumps, sha256_hex
from adam_os.inference.policy_gate import enforce_policy_gate


def _is_hex64(s: str) -> bool:
    if not isinstance(s, str) or len(s) != 64:
        return False
    try:
        int(s, 16)
        return True
    except Exception:
        return False


def build_inference_request(tool_input: Dict[str, Any]) -> Dict[str, Any]:
    if not isinstance(tool_input, dict):
        raise TypeError("tool_input must be dict")

    created_at_utc = tool_input.get("created_at_utc")
    if not isinstance(created_at_utc, str) or not created_at_utc.strip():
        raise ValueError("tool_input.created_at_utc must be injected")

    snapshot_hash = tool_input.get("snapshot_hash")
    if not isinstance(snapshot_hash, str) or not _is_hex64(snapshot_hash):
        raise ValueError("tool_input.snapshot_hash must be a 64-hex string")

    provider = tool_input.get("provider")
    if not isinstance(provider, str) or not provider.strip():
        raise ValueError("tool_input.provider must be a non-empty string")

    model = tool_input.get("model")
    if not isinstance(model, str) or not model.strip():
        raise ValueError("tool_input.model must be a non-empty string (no aliases)")

    system_prompt = tool_input.get("system_prompt")
    if not isinstance(system_prompt, str):
        raise ValueError("tool_input.system_prompt must be a string (can be empty)")

    user_prompt = tool_input.get("user_prompt")
    if not isinstance(user_prompt, str) or not user_prompt.strip():
        raise ValueError("tool_input.user_prompt must be a non-empty string")

    temperature = tool_input.get("temperature")
    if not isinstance(temperature, (int, float)):
        raise ValueError("tool_input.temperature must be a number")

    max_tokens = tool_input.get("max_tokens")
    if not isinstance(max_tokens, int) or max_tokens <= 0:
        raise ValueError("tool_input.max_tokens must be a positive int")

    provider_max_tokens_cap = tool_input.get("provider_max_tokens_cap")
    if not isinstance(provider_max_tokens_cap, int) or provider_max_tokens_cap <= 0:
        raise ValueError("tool_input.provider_max_tokens_cap must be injected (positive int)")

    request_id = tool_input.get("request_id")
    if request_id is not None and (not isinstance(request_id, str) or not request_id.strip()):
        raise ValueError("tool_input.request_id must be a non-empty string if provided")

    # Policy Gate (SPEC-008D)
    policy = enforce_policy_gate(
        provider=provider.strip(),
        model=model.strip(),
        temperature=float(temperature),
        max_tokens=int(max_tokens),
        provider_max_tokens_cap=int(provider_max_tokens_cap),
    )

    req: Dict[str, Any] = {
        "kind": "inference.request",
        "created_at_utc": created_at_utc,
        "snapshot_hash": snapshot_hash,
        "provider": policy["provider"],
        "model": policy["model"],
        "params": {
            "temperature": policy["temperature"],
            "max_tokens": policy["max_tokens"],
        },
        "prompts": {
            "system_prompt": system_prompt,
            "user_prompt": user_prompt,
        },
    }

    # Deterministic request hash (contract-friendly identifier)
    req_hash = sha256_hex(canonical_dumps(req))
    req["request_hash"] = req_hash

    # If caller didn't supply request_id, bind to request_hash
    if request_id is None:
        req["request_id"] = req_hash
    else:
        req["request_id"] = request_id.strip()

    return req
