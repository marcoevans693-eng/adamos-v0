# Procedure: Phase 9 tool - inference.execute (bridges Phase 8 request artifacts to real provider calls)
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict

from adam_os.providers.openai_responses import OpenAIHTTPError
from adam_os.providers.anthropic_messages import AnthropicHTTPError
from adam_os.providers.dispatch import dispatch_text
from adam_os.tools.inference_response_emit import inference_response_emit
from adam_os.tools.inference_error_emit import inference_error_emit
from adam_os.tools.inference_receipt_emit import inference_receipt_emit


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
      - Call provider (Phase 9 network boundary via dispatch)
      - Emit Phase 8 response/error artifacts (unchanged contracts)
      - ALWAYS emit Phase 8 receipt artifact (unchanged contract)
    """
    if not isinstance(tool_input, dict):
        raise TypeError("tool_input must be dict")

    created_at_utc = tool_input.get("created_at_utc")
    if not isinstance(created_at_utc, str) or not created_at_utc.strip():
        raise ValueError("tool_input.created_at_utc must be injected")

    request_id = tool_input.get("request_id")
    if not isinstance(request_id, str) or not request_id.strip():
        raise ValueError("tool_input.request_id must be a non-empty string")

    request_id_s = request_id.strip()
    created_at_utc_s = created_at_utc.strip()

    req = _load_request(request_id_s)

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

    provider_s = provider.strip()
    model_s = model.strip()

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

    response_id = f"{request_id_s}--response"
    error_id = f"{request_id_s}--error"

    try:
        # Provider execution via dispatch (OpenAI now; more later)
        r = dispatch_text(
            provider=provider_s,
            model=model_s,
            user_input=user_prompt,
            instructions=system_prompt,
            temperature=float(temperature),
            max_output_tokens=int(max_tokens),
        )

        out_resp = inference_response_emit(
            {
                "created_at_utc": created_at_utc_s,
                "request_id": request_id_s,
                "request_hash": request_hash,
                "snapshot_hash": snapshot_hash,
                "provider": r.provider,
                "model": r.model,
                "output_text": r.output_text,
                "response_id": response_id,
            }
        )

        out_receipt = inference_receipt_emit(
            {
                "created_at_utc": created_at_utc_s,
                "request_id": request_id_s,
                "request_hash": request_hash,
                "snapshot_hash": snapshot_hash,
                "provider": r.provider,
                "model": r.model,
                "response_id": response_id,
            }
        )

        return {
            "ok": True,
            "provider_response_id": r.provider_response_id,
            "emitted_response": out_resp,
            "emitted_receipt": out_receipt,
        }

    except OpenAIHTTPError as e:
        out_err = inference_error_emit(
            {
                "created_at_utc": created_at_utc_s,
                "request_id": request_id_s,
                "request_hash": request_hash,
                "snapshot_hash": snapshot_hash,
                "provider": provider_s,
                "model": model_s,
                "error_type": "provider_http_error",
                "message": str(e),
                "error_id": error_id,
            }
        )

        out_receipt = inference_receipt_emit(
            {
                "created_at_utc": created_at_utc_s,
                "request_id": request_id_s,
                "request_hash": request_hash,
                "snapshot_hash": snapshot_hash,
                "provider": provider_s,
                "model": model_s,
                "error_id": error_id,
            }
        )

        return {"ok": False, "emitted_error": out_err, "emitted_receipt": out_receipt}


    except AnthropicHTTPError as e:
        out_err = inference_error_emit(
            {
                "created_at_utc": created_at_utc_s,
                "request_id": request_id_s,
                "request_hash": request_hash,
                "snapshot_hash": snapshot_hash,
                "provider": provider_s,
                "model": model_s,
                "error_type": "provider_http_error",
                "message": str(e),
                "error_id": error_id,
            }
        )

        out_receipt = inference_receipt_emit(
            {
                "created_at_utc": created_at_utc_s,
                "request_id": request_id_s,
                "request_hash": request_hash,
                "snapshot_hash": snapshot_hash,
                "provider": provider_s,
                "model": model_s,
                "error_id": error_id,
            }
        )

        return {"ok": False, "emitted_error": out_err, "emitted_receipt": out_receipt}

    except ValueError as e:
        msg = str(e)

        # Step 8 fix: Anthropic preflight config failures (e.g., missing key) must normalize
        # to provider_http_error for parity with OpenAIHTTPError normalization.
        if provider_s == "anthropic" and (msg.startswith("ANTHROPIC_") or msg.startswith("anthropic_")):
            out_err = inference_error_emit(
                {
                    "created_at_utc": created_at_utc_s,
                    "request_id": request_id_s,
                    "request_hash": request_hash,
                    "snapshot_hash": snapshot_hash,
                    "provider": provider_s,
                    "model": model_s,
                    "error_type": "provider_http_error",
                    "message": msg,
                    "error_id": error_id,
                }
            )
            out_receipt = inference_receipt_emit(
                {
                    "created_at_utc": created_at_utc_s,
                    "request_id": request_id_s,
                    "request_hash": request_hash,
                    "snapshot_hash": snapshot_hash,
                    "provider": provider_s,
                    "model": model_s,
                    "error_id": error_id,
                }
            )
            return {"ok": False, "emitted_error": out_err, "emitted_receipt": out_receipt}

        out_err = inference_error_emit(
            {
                "created_at_utc": created_at_utc_s,
                "request_id": request_id_s,
                "request_hash": request_hash,
                "snapshot_hash": snapshot_hash,
                "provider": provider_s,
                "model": model_s,
                "error_type": "inference_execute_error",
                "message": msg,
                "error_id": error_id,
            }
        )
        out_receipt = inference_receipt_emit(
            {
                "created_at_utc": created_at_utc_s,
                "request_id": request_id_s,
                "request_hash": request_hash,
                "snapshot_hash": snapshot_hash,
                "provider": provider_s,
                "model": model_s,
                "error_id": error_id,
            }
        )
        return {"ok": False, "emitted_error": out_err, "emitted_receipt": out_receipt}

    except Exception as e:
        msg = str(e)
        etype = "provider_http_error" if provider_s == "anthropic" and (msg.startswith("ANTHROPIC_") or msg.startswith("anthropic_")) else "inference_execute_error"

        out_err = inference_error_emit(
            {
                "created_at_utc": created_at_utc_s,
                "request_id": request_id_s,
                "request_hash": request_hash,
                "snapshot_hash": snapshot_hash,
                "provider": provider_s,
                "model": model_s,
                "error_type": etype,
                "message": msg,
                "error_id": error_id,
            }
        )

        out_receipt = inference_receipt_emit(
            {
                "created_at_utc": created_at_utc_s,
                "request_id": request_id_s,
                "request_hash": request_hash,
                "snapshot_hash": snapshot_hash,
                "provider": provider_s,
                "model": model_s,
                "error_id": error_id,
            }
        )

        return {"ok": False, "emitted_error": out_err, "emitted_receipt": out_receipt}
