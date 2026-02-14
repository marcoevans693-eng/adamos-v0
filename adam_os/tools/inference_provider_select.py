"""
Phase 8 Step 4 tool - inference.provider_select

Tool name: "inference.provider_select"

Goal:
- Deterministically select provider configuration inputs needed by inference.request_emit.
- Provide provider_max_tokens_cap without network calls or SDK imports.
- No provider calls. No ledger writes. No registry writes.
"""

from __future__ import annotations

from typing import Any, Dict


TOOL_NAME = "inference.provider_select"

# Conservative v0 caps (injected deterministically; updated later when real adapters exist)
PROVIDER_TOKEN_CAPS = {
    "openai": 8192,
    "anthropic": 8192,
}


def inference_provider_select(tool_input: Dict[str, Any]) -> Dict[str, Any]:
    if not isinstance(tool_input, dict):
        raise TypeError("tool_input must be dict")

    provider = tool_input.get("provider")
    if not isinstance(provider, str) or not provider.strip():
        raise ValueError("tool_input.provider must be a non-empty string")

    p = provider.strip()
    if p not in PROVIDER_TOKEN_CAPS:
        raise ValueError("provider_select_reject: provider must be 'openai' or 'anthropic'")

    return {
        "provider": p,
        "provider_max_tokens_cap": int(PROVIDER_TOKEN_CAPS[p]),
        "notes": "phase8_step4: deterministic provider selection (no network)",
    }
