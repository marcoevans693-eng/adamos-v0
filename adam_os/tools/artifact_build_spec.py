# Procedure: Phase 7 Step 8 tool - artifact.build_spec (BUILD_SPEC artifact; prompt_hash + audit meta; registry append-only)
"""
Artifact build-spec tool (Phase 7 Step 8)

Tool name: "artifact.build_spec"

Goal:
- Generate an auditable BUILD_SPEC artifact from a BUNDLE_MANIFEST (Step 7 output).
- Capture governed inference metadata + deterministic prompt_hash.
- Preserve strict lineage + registry traceability.

Hard rules:
- Writes ONLY under .adam_os/artifacts/specs/
- Appends ONLY to .adam_os/artifacts/artifact_registry.jsonl
- No system clock reads; created_at_utc must be injected
- Deterministic hashing via canonical_dumps + sha256
- Idempotent: if spec file exists AND registry already has BUILD_SPEC record, do not append again.

Inputs:
- created_at_utc: str (required; injected)
- bundle_artifact_id: str (required; Step 7 bundle id; file at .adam_os/artifacts/bundles/<id>.json)
- provider: str (required; captured metadata)
- model: str (required; captured metadata)
- temperature: number (optional; captured metadata)
- max_tokens: int (optional; captured metadata)
- spec_artifact_id: str (optional; default "<bundle_id>--build_spec")
- media_type: str (optional; default "application/json")

Optional override for deterministic "inference output" (used by proof / offline mode):
- inferred_notes: str (optional; if absent, inferred sections remain empty)

Output BUILD_SPEC must include:
- SOURCE-BASED vs INFERRED vs ASSUMPTION separation
- OPEN QUESTIONS list (can be empty)
- SOURCE MAP: sections -> artifact IDs + sha256 + kind
- Audit meta: provider/model/temperature/max_tokens/prompt_hash/bundle_hash/spec_sha256
"""

from __future__ import annotations

import json
import hashlib
from pathlib import Path
from typing import Any, Dict, Optional

from adam_os.artifacts.registry import ArtifactRegistry, sha256_file, file_size_bytes
from adam_os.memory.canonical import canonical_dumps, sha256_hex


TOOL_NAME = "artifact.build_spec"

ARTIFACT_ROOT = Path(".adam_os") / "artifacts"
BUNDLES_DIR = ARTIFACT_ROOT / "bundles"
SPECS_DIR = ARTIFACT_ROOT / "specs"

DEFAULT_MEDIA_TYPE = "application/json"


def _registry_has(registry_path: Path, artifact_id: str, kind: str) -> bool:
    if not registry_path.exists():
        return False
    needle_id = f"\"artifact_id\":\"{artifact_id}\""
    needle_kind = f"\"kind\":\"{kind}\""
    with registry_path.open("r", encoding="utf-8") as f:
        for line in f:
            if needle_id in line and needle_kind in line:
                return True
    return False


def _sha256_text(s: str) -> str:
    return hashlib.sha256(s.encode("utf-8")).hexdigest()


def _read_bundle_manifest(bundle_path: Path) -> Dict[str, Any]:
    if not bundle_path.exists():
        raise ValueError(f"bundle manifest file not found: {bundle_path}")
    try:
        obj = json.loads(bundle_path.read_text(encoding="utf-8"))
    except Exception as e:
        raise ValueError(f"bundle manifest is not valid JSON: {e}") from None
    if not isinstance(obj, dict):
        raise ValueError("bundle manifest must be a JSON object")
    if obj.get("kind") != "BUNDLE_MANIFEST":
        raise ValueError("bundle manifest kind must be BUNDLE_MANIFEST")
    if not isinstance(obj.get("bundle_hash"), str) or len(obj["bundle_hash"]) != 64:
        raise ValueError("bundle manifest missing valid bundle_hash")
    members = obj.get("members")
    if not isinstance(members, list):
        raise ValueError("bundle manifest members must be a list")
    for m in members:
        if not isinstance(m, dict):
            raise ValueError("bundle manifest members must be objects")
        if not isinstance(m.get("artifact_id"), str) or not m["artifact_id"]:
            raise ValueError("bundle member missing artifact_id")
        if not isinstance(m.get("sha256"), str) or len(m["sha256"]) != 64:
            raise ValueError("bundle member missing valid sha256")
        if not isinstance(m.get("kind"), str) or not m["kind"]:
            raise ValueError("bundle member missing kind")
        if not isinstance(m.get("byte_size"), int) or m["byte_size"] < 0:
            raise ValueError("bundle member missing valid byte_size")
    return obj


def _normalize_temperature(v: Any) -> Optional[float]:
    if v is None:
        return None
    if isinstance(v, bool):
        raise ValueError("temperature must be a number, not bool")
    if isinstance(v, (int, float)):
        return float(v)
    raise ValueError("temperature must be a number")


def _normalize_max_tokens(v: Any) -> Optional[int]:
    if v is None:
        return None
    if isinstance(v, bool):
        raise ValueError("max_tokens must be an int, not bool")
    if isinstance(v, int):
        if v < 0:
            raise ValueError("max_tokens must be >= 0")
        return int(v)
    raise ValueError("max_tokens must be an int")


def _frozen_prompt_template() -> Dict[str, Any]:
    return {
        "template_id": "PHASE7_STEP8_BUILD_SPEC_V1",
        "intent": "Convert bundle manifest into an auditable BUILD_SPEC with strict separation of source-based vs inferred vs assumptions; include open questions and a source map.",
        "required_sections": ["SOURCE_BASED", "INFERRED", "ASSUMPTIONS", "OPEN_QUESTIONS", "SOURCE_MAP"],
        "rules": [
            "Do not invent facts; put unknowns into OPEN_QUESTIONS.",
            "Every claim in SOURCE_BASED must trace to bundle members (artifact_id + sha256).",
            "INFERRED must be explicitly labeled as inference.",
            "ASSUMPTIONS must be explicitly labeled as assumptions.",
        ],
    }


def artifact_build_spec(tool_input: Dict[str, Any]) -> Dict[str, Any]:
    if not isinstance(tool_input, dict):
        raise TypeError("tool_input must be dict")

    created_at_utc = tool_input.get("created_at_utc")
    if not isinstance(created_at_utc, str) or not created_at_utc.strip():
        raise ValueError("tool_input.created_at_utc must be a non-empty injected string")

    media_type = tool_input.get("media_type") or DEFAULT_MEDIA_TYPE
    if not isinstance(media_type, str) or not media_type.strip():
        raise ValueError("tool_input.media_type must be a non-empty string")

    bundle_artifact_id = tool_input.get("bundle_artifact_id")
    if not isinstance(bundle_artifact_id, str) or not bundle_artifact_id.strip():
        raise ValueError("tool_input.bundle_artifact_id must be a non-empty string")
    bundle_id = bundle_artifact_id.strip()

    provider = tool_input.get("provider")
    if not isinstance(provider, str) or not provider.strip():
        raise ValueError("tool_input.provider must be a non-empty string")

    model = tool_input.get("model")
    if not isinstance(model, str) or not model.strip():
        raise ValueError("tool_input.model must be a non-empty string")

    temperature = _normalize_temperature(tool_input.get("temperature"))
    max_tokens = _normalize_max_tokens(tool_input.get("max_tokens"))

    spec_artifact_id = tool_input.get("spec_artifact_id") or f"{bundle_id}--build_spec"
    if not isinstance(spec_artifact_id, str) or not spec_artifact_id.strip():
        raise ValueError("tool_input.spec_artifact_id must be a non-empty string if provided")
    spec_id = spec_artifact_id.strip()

    inferred_notes = tool_input.get("inferred_notes")
    if inferred_notes is not None and not isinstance(inferred_notes, str):
        raise ValueError("tool_input.inferred_notes must be a string if provided")

    SPECS_DIR.mkdir(parents=True, exist_ok=True)
    spec_path = SPECS_DIR / f"{spec_id}.json"

    reg = ArtifactRegistry(artifact_root=ARTIFACT_ROOT)

    # Idempotency gate (no duplicate registry append)
    if spec_path.exists() and _registry_has(reg.registry_path, spec_id, "BUILD_SPEC"):
        sha = sha256_file(spec_path)
        size = file_size_bytes(spec_path)
        try:
            obj = json.loads(spec_path.read_text(encoding="utf-8"))
            prompt_hash = obj.get("audit", {}).get("prompt_hash")
            bundle_hash = obj.get("bundle", {}).get("bundle_hash")
        except Exception:
            prompt_hash = None
            bundle_hash = None
        return {
            "artifact_id": spec_id,
            "kind": "BUILD_SPEC",
            "bundle_artifact_id": bundle_id,
            "spec_path": str(spec_path),
            "registry_path": str(reg.registry_path),
            "sha256": sha,
            "byte_size": size,
            "media_type": media_type,
            "prompt_hash": prompt_hash,
            "bundle_hash": bundle_hash,
        }

    bundle_path = BUNDLES_DIR / f"{bundle_id}.json"
    bundle_obj = _read_bundle_manifest(bundle_path)
    bundle_hash = bundle_obj["bundle_hash"]
    members = bundle_obj["members"]

    prompt_payload = {
        "template": _frozen_prompt_template(),
        "bundle_manifest": {
            "bundle_id": bundle_obj.get("bundle_id", bundle_id),
            "bundle_hash": bundle_hash,
            "members": members,
        },
        "inference_settings": {
            "provider": provider.strip(),
            "model": model.strip(),
            "temperature": temperature,
            "max_tokens": max_tokens,
        },
    }
    prompt_canon = canonical_dumps(prompt_payload)
    prompt_hash = sha256_hex(prompt_canon)

    source_map = {
        "SOURCE_BASED": list(members),
        "INFERRED": list(members),
        "ASSUMPTIONS": list(members),
        "OPEN_QUESTIONS": list(members),
    }

    build_spec_obj: Dict[str, Any] = {
        "artifact_id": spec_id,
        "kind": "BUILD_SPEC",
        "created_at_utc": created_at_utc,
        "bundle": {
            "bundle_artifact_id": bundle_id,
            "bundle_hash": bundle_hash,
        },
        "audit": {
            "provider": provider.strip(),
            "model": model.strip(),
            "temperature": temperature,
            "max_tokens": max_tokens,
            "prompt_hash": prompt_hash,
        },
        "spec": {
            "SOURCE_BASED": {
                "claims": [],
                "notes": "Empty by default; populate via governed inference layer in a future adapter, without changing schema.",
            },
            "INFERRED": {
                "claims": [],
                "notes": (inferred_notes or ""),
            },
            "ASSUMPTIONS": {
                "claims": [],
                "notes": "Empty by default; assumptions belong here (explicitly labeled).",
            },
            "OPEN_QUESTIONS": [],
            "SOURCE_MAP": source_map,
        },
        "notes": "artifact.build_spec",
        "tags": ["phase7", "build_spec", "governed_inference_meta"],
    }

    spec_text = canonical_dumps(build_spec_obj) + "\n"
    spec_path.write_text(spec_text, encoding="utf-8")

    sha = sha256_file(spec_path)
    size = file_size_bytes(spec_path)

    reg.append_from_file(
        artifact_id=spec_id,
        kind="BUILD_SPEC",
        created_at_utc=created_at_utc,
        file_path=spec_path,
        media_type=media_type,
        parent_artifact_ids=[bundle_id],
        notes="artifact.build_spec",
        tags=["phase7", "build_spec"],
    )

    return {
        "artifact_id": spec_id,
        "kind": "BUILD_SPEC",
        "bundle_artifact_id": bundle_id,
        "bundle_hash": bundle_hash,
        "spec_path": str(spec_path),
        "registry_path": str(reg.registry_path),
        "sha256": sha,
        "byte_size": size,
        "media_type": media_type,
        "prompt_hash": prompt_hash,
    }
