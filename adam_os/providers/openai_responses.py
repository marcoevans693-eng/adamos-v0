# Procedure: OpenAI Responses API adapter (Phase 9 runtime; network boundary)
from __future__ import annotations

import json
import os
import time
import urllib.error
import urllib.request
from dataclasses import dataclass
from typing import Any, Dict, Optional


OPENAI_RESPONSES_URL = "https://api.openai.com/v1/responses"


class OpenAIHTTPError(RuntimeError):
    pass


@dataclass(frozen=True)
class OpenAIResponse:
    response_id: str
    model: str
    output_text: str
    raw: Dict[str, Any]


def _extract_output_text(resp: Dict[str, Any]) -> str:
    """
    Extract aggregated assistant text from Responses API payload.

    We do NOT rely on SDK-only `output_text`.
    We parse `output[] -> message -> content[] -> output_text.text`.
    """
    out_parts = []

    output = resp.get("output")
    if isinstance(output, list):
        for item in output:
            if not isinstance(item, dict):
                continue
            if item.get("type") != "message":
                continue
            if item.get("role") != "assistant":
                continue
            content = item.get("content")
            if not isinstance(content, list):
                continue
            for c in content:
                if not isinstance(c, dict):
                    continue
                if c.get("type") == "output_text" and isinstance(c.get("text"), str):
                    out_parts.append(c["text"])

    return "\n".join([p for p in out_parts if p is not None]).strip()


def responses_create_text(
    *,
    model: str,
    user_input: str,
    instructions: str,
    temperature: float,
    max_output_tokens: int,
    timeout_s: int = 60,
    store: bool = False,
    api_key: Optional[str] = None,
) -> OpenAIResponse:
    """
    Minimal Responses API call for text-only inference.

    Uses:
      - `input` as a string (equivalent to a user message)
      - `instructions` as system/developer guidance
      - `temperature`
      - `max_output_tokens`

    Auth via OPENAI_API_KEY env var by default.
    """
    key = api_key or os.environ.get("OPENAI_API_KEY") or ""
    if not key.strip():
        raise OpenAIHTTPError("missing_openai_api_key: OPENAI_API_KEY is not set")

    if not isinstance(model, str) or not model.strip():
        raise ValueError("model must be non-empty")
    if not isinstance(user_input, str) or not user_input.strip():
        raise ValueError("user_input must be non-empty")
    if not isinstance(instructions, str):
        raise ValueError("instructions must be a string (can be empty)")
    if not isinstance(temperature, (int, float)):
        raise ValueError("temperature must be number")
    if not isinstance(max_output_tokens, int) or max_output_tokens <= 0:
        raise ValueError("max_output_tokens must be positive int")

    body = {
        "model": model.strip(),
        "input": user_input,
        "instructions": instructions,
        "temperature": float(temperature),
        "max_output_tokens": int(max_output_tokens),
        "store": bool(store),
    }

    data = json.dumps(body, ensure_ascii=False, separators=(",", ":"), sort_keys=True).encode("utf-8")
    req = urllib.request.Request(
        OPENAI_RESPONSES_URL,
        data=data,
        method="POST",
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {key.strip()}",
        },
    )

    t0 = time.time()
    try:
        with urllib.request.urlopen(req, timeout=timeout_s) as r:
            raw_bytes = r.read()
            payload = json.loads(raw_bytes.decode("utf-8"))
    except urllib.error.HTTPError as e:
        # Try to include response body for diagnostics (without leaking key)
        try:
            msg = e.read().decode("utf-8", errors="replace")
        except Exception:
            msg = str(e)
        raise OpenAIHTTPError(f"openai_http_error: {e.code} {e.reason}: {msg}") from e
    except Exception as e:
        raise OpenAIHTTPError(f"openai_request_failed: {e}") from e
    finally:
        _ = (time.time() - t0)

    resp_id = payload.get("id")
    resp_model = payload.get("model")
    if not isinstance(resp_id, str) or not resp_id.strip():
        resp_id = "unknown"
    if not isinstance(resp_model, str) or not resp_model.strip():
        resp_model = model.strip()

    text = _extract_output_text(payload)

    return OpenAIResponse(
        response_id=resp_id,
        model=resp_model,
        output_text=text,
        raw=payload if isinstance(payload, dict) else {"raw": payload},
    )
