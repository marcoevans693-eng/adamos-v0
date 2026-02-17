# Procedure: provider dispatch for Phase 9 (routes provider+model to implementation without contract drift)
from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Dict

from adam_os.providers.openai_responses import responses_create_text


@dataclass(frozen=True)
class ProviderTextResult:
    provider: str
    model: str
    provider_response_id: str
    output_text: str


def _call_openai_text(
    *,
    model: str,
    user_input: str,
    instructions: str,
    temperature: float,
    max_output_tokens: int,
) -> ProviderTextResult:
    r = responses_create_text(
        model=model,
        user_input=user_input,
        instructions=instructions,
        temperature=float(temperature),
        max_output_tokens=int(max_output_tokens),
        timeout_s=60,
        store=False,
    )
    return ProviderTextResult(
        provider="openai",
        model=r.model,
        provider_response_id=r.response_id,
        output_text=r.output_text,
    )


_TEXT_DISPATCH: Dict[str, Callable[..., ProviderTextResult]] = {
    "openai": _call_openai_text,
}


def dispatch_text(
    *,
    provider: str,
    model: str,
    user_input: str,
    instructions: str,
    temperature: float,
    max_output_tokens: int,
) -> ProviderTextResult:
    """
    Single provider-agnostic entrypoint for text execution.

    - Fail-closed on unknown provider.
    - No policy changes here; policy gate remains upstream (request_emit).
    """
    if not isinstance(provider, str) or not provider.strip():
        raise ValueError("dispatch_text_invalid_provider")
    p = provider.strip()

    fn = _TEXT_DISPATCH.get(p)
    if fn is None:
        raise ValueError(f"dispatch_text_unsupported_provider: {p}")

    return fn(
        model=model,
        user_input=user_input,
        instructions=instructions,
        temperature=temperature,
        max_output_tokens=max_output_tokens,
    )
