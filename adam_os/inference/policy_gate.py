"""
adam_os.inference.policy_gate

Phase 8 Policy Gate (SPEC-008D)

Enforces:
- Explicit model allowlist per provider
- Parameter ceilings: temperature in [0.0, 1.0]
- max_tokens > 0 and <= provider hard cap

No provider calls. No ledger writes.
Raises ValueError on rejection (fail-closed).
"""

from __future__ import annotations

from typing import Any, Dict


OPENAI_ALLOWED_MODELS = {
    "gpt-4o",
    "gpt-4.1",
    "gpt-4.1-mini",
}

ANTHROPIC_ALLOWED_MODELS = {
    "claude-3-opus",
    "claude-3-sonnet",
    "claude-3-haiku",
}


def enforce_policy_gate(*, provider: str, model: str, temperature: float, max_tokens: int, provider_max_tokens_cap: int) -> Dict[str, Any]:
    # Provider
    if provider not in {"openai", "anthropic"}:
        raise ValueError("policy_reject: provider must be 'openai' or 'anthropic'")

    # Model allowlist (exact match)
    allowed = OPENAI_ALLOWED_MODELS if provider == "openai" else ANTHROPIC_ALLOWED_MODELS
    if model not in allowed:
        raise ValueError("policy_reject: model not allowlisted by SPEC-008D")

    # Temperature bounds
    if not isinstance(temperature, (int, float)):
        raise ValueError("policy_reject: temperature must be numeric")
    t = float(temperature)
    if t < 0.0 or t > 1.0:
        raise ValueError("policy_reject: temperature out of bounds [0.0, 1.0]")

    # max_tokens bounds + provider cap
    if not isinstance(max_tokens, int) or max_tokens <= 0:
        raise ValueError("policy_reject: max_tokens must be a positive int")

    if not isinstance(provider_max_tokens_cap, int) or provider_max_tokens_cap <= 0:
        # We do not guess provider caps in v0; adapters will later supply them.
        raise ValueError("policy_reject: provider_max_tokens_cap must be injected (positive int)")

    if max_tokens > provider_max_tokens_cap:
        raise ValueError("policy_reject: max_tokens exceeds provider hard cap")

    return {
        "provider": provider,
        "model": model,
        "temperature": t,
        "max_tokens": int(max_tokens),
        "provider_max_tokens_cap": int(provider_max_tokens_cap),
    }
