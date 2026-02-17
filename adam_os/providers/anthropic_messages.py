# Procedure: Anthropic Messages API (Phase 9 provider module) — minimal text-only wrapper
from __future__ import annotations

import json
import os
import urllib.error
import urllib.request
from dataclasses import dataclass
from typing import Any, Dict, Optional


class AnthropicHTTPError(RuntimeError):
    pass


@dataclass(frozen=True)
class AnthropicTextResult:
    model: str
    message_id: str
    output_text: str


def messages_create_text(
    *,
    model: str,
    user_input: str,
    system: str,
    max_tokens: int,
    temperature: float,
    timeout_s: int = 60,
) -> AnthropicTextResult:
    """
    Minimal Messages API call.

    - Uses ANTHROPIC_API_KEY from environment.
    - Text-only: system + one user message.
    - Fail-closed on any non-200 response.
    """
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not isinstance(api_key, str) or not api_key.strip():
        raise ValueError("ANTHROPIC_API_KEY_missing")

    if not isinstance(model, str) or not model.strip():
        raise ValueError("anthropic_model_invalid")
    if not isinstance(user_input, str) or not user_input.strip():
        raise ValueError("anthropic_user_input_invalid")
    if not isinstance(system, str):
        raise ValueError("anthropic_system_invalid")
    if not isinstance(max_tokens, int) or max_tokens <= 0:
        raise ValueError("anthropic_max_tokens_invalid")
    if not isinstance(temperature, (int, float)):
        raise ValueError("anthropic_temperature_invalid")

    url = "https://api.anthropic.com/v1/messages"
    payload: Dict[str, Any] = {
        "model": model.strip(),
        "max_tokens": int(max_tokens),
        "temperature": float(temperature),
        "system": system,
        "messages": [{"role": "user", "content": user_input}],
    }

    body = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(url, data=body, method="POST")
    req.add_header("content-type", "application/json")
    req.add_header("x-api-key", api_key.strip())
    req.add_header("anthropic-version", "2023-06-01")

    try:
        with urllib.request.urlopen(req, timeout=timeout_s) as resp:
            raw = resp.read()
            data = json.loads(raw.decode("utf-8"))

    except urllib.error.HTTPError as e:
        msg = e.read().decode("utf-8", errors="replace") if hasattr(e, "read") else str(e)
        raise AnthropicHTTPError(f"anthropic_http_error: {e.code}: {msg}") from e
    except Exception as e:
        raise AnthropicHTTPError(f"anthropic_transport_error: {e}") from e

    if not isinstance(data, dict):
        raise AnthropicHTTPError("anthropic_invalid_json: not an object")

    message_id = data.get("id")
    out_model = data.get("model") or model.strip()
    content = data.get("content")

    if not isinstance(message_id, str) or not message_id.strip():
        raise AnthropicHTTPError("anthropic_missing_message_id")
    if not isinstance(content, list) or not content:
        raise AnthropicHTTPError("anthropic_missing_content")

    # content items typically look like: {"type":"text","text":"..."}
    text_parts = []
    for item in content:
        if isinstance(item, dict) and item.get("type") == "text" and isinstance(item.get("text"), str):
            text_parts.append(item["text"])

    output_text = "".join(text_parts)
    if not isinstance(output_text, str):
        raise AnthropicHTTPError("anthropic_output_text_invalid")

    return AnthropicTextResult(model=str(out_model), message_id=message_id, output_text=output_text)
