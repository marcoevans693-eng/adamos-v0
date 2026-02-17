# Procedure: Phase 9 tool - inference.execute (bridges Phase 8 request artifacts to real provider calls)
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict

from adam_os.providers.openai_responses import OpenAIHTTPError, responses_create_text
from adam_os.tools.inference_response_emit import inference_response_emit
from adam_os.tools.inference_error_emit import inference_error_emit


TOOL_NAME = "inference.execute"

INFERENCE_ROOT = Path(".adam_os") / "inference"
REQUESTS_DIR = INFERENCE_ROOT / "requests"


def _load_request(request_id: str) -> Dict[str, Any]:
    req_path = REQUESTS_DIR / f"{request_id}.json"
    if not req_path.exists():
        raise ValueError(f"inference_execute_missing_request: {req_path}")

    obj = json.loads(req_path.read_text(encoding="utf-8"))
    if not isinstance(obj, dict):
        raise ValueError("inference_execute_invalid_request_json: not an object")

    if obj.get("kind") != "inference.request":
        raise ValueError("inference_execute_invalid_request_kind: expected inference.request")

    return obj


def inference_execute(tool_input: Dict[str, Any]) -> Dict[str, Any]:
    """
    Tool name: inference.execute

    Inputs:
      - created_at_utc (string, non-empty)  [for emitters]
      - request_id (string, non-empty)      [must already exist under .adam_os/inference/requests/]

    Behavior:
      - Load Phase 8 request artifact JSON
      - Call provider (Phase 9 network boundary)
      - Emit Phase 8 response/error artifacts (unchanged contracts)
    """
    if not isinstance(tool_input, dict):
        raise TypeError("tool_input must be dict")

    created_at_utc = tool_input.get("created_at_utc")
    if not isinstance(created_at_utc, str) or not created_at_utc.strip():
        raise ValueError("tool_input.created_at_utc must be injected")

    request_id = tool_input.get("request_id")
    if not isinstance(request_id, str) or not request_id.strip():
        raise ValueError("tool_input.request_id must be a non-empty string")

    req = _load_request(request_id.strip())

    provider = req.get("provider")
    model = req.get("model")
    snapshot_hash = req.get("snapshot_hash")
    request_hash = req.get("request_hash")
    params = req.get("params") or {}
    prompts = req.get("prompts") or {}

    if not isinstance(provider, str) or not provider.strip():
        raise ValueError("inference_execute_request_missing_provider")
    if not isinstance(model, str) or not model.strip():
        raise ValueError("inference_execute_request_missing_model")
    if not isinstance(snapshot_hash, str) or len(snapshot_hash) != 64:
        raise ValueError("inference_execute_request_missing_snapshot_hash")
    if not isinstance(request_hash, str) or len(request_hash) != 64:
        raise ValueError("inference_execute_request_missing_request_hash")

    temperature = params.get("temperature")
    max_tokens = params.get("max_tokens")

    if not isinstance(temperature, (int, float)):
        raise ValueError("inference_execute_request_missing_temperature")
    if not isinstance(max_tokens, int) or max_tokens <= 0:
        raise ValueError("inference_execute_request_missing_max_tokens")

    system_prompt = prompts.get("system_prompt", "")
    user_prompt = prompts.get("user_prompt", "")
    if not isinstance(system_prompt, str):
        raise ValueError("inference_execute_request_system_prompt_invalid")
    if not isinstance(user_prompt, str) or not user_prompt.strip():
        raise ValueError("inference_execute_request_user_prompt_invalid")

    # Phase 9 provider execution (OpenAI first; Anthropic later)
    try:
        if provider.strip() != "openai":
            raise ValueError("inference_execute_provider_unsupported: only 'openai' is implemented in phase9_step1")

        r = responses_create_text(
            model=model.strip(),
            user_input=user_prompt,
            instructions=system_prompt,
            temperature=float(temperature),
            max_output_tokens=int(max_tokens),
            timeout_s=60,
            store=False,
        )

        # Emit Phase 8 response artifact (contract preserved)
        out = inference_response_emit(
            {
                "created_at_utc": created_at_utc.strip(),
                "request_id": request_id.strip(),
                "request_hash": request_hash,
                "snapshot_hash": snapshot_hash,
                "provider": provider.strip(),
                "model": r.model,
                "output_text": r.output_text,
                "response_id": f"{request_id.strip()}--response",
            }
        )

        return {
            "ok": True,
            "provider_response_id": r.response_id,
            "emitted": out,
        }

    except OpenAIHTTPError as e:
        err = inference_error_emit(
            {
                "created_at_utc": created_at_utc.strip(),
                "request_id": request_id.strip(),
                "request_hash": request_hash,
                "snapshot_hash": snapshot_hash,
                "provider": provider.strip(),
                "model": model.strip(),
                "error_type": "provider_http_error",
                "message": str(e),
                "error_id": f"{request_id.strip()}--error",
            }
        )
        return {"ok": False, "emitted": err}

    except Exception as e:
        err = inference_error_emit(
            {
                "created_at_utc": created_at_utc.strip(),
                "request_id": request_id.strip(),
                "request_hash": request_hash,
                "snapshot_hash": snapshot_hash,
                "provider": provider.strip(),
                "model": model.strip(),
                "error_type": "inference_execute_error",
                "message": str(e),
                "error_id": f"{request_id.strip()}--error",
            }
        )
        return {"ok": False, "emitted": err}
