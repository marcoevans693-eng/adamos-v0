# Procedure: Phase 7 Step 9 tool - artifact.work_order_emit (WORK_ORDER artifact; deterministic; registry append-only)
"""
Artifact work-order-emit tool (Phase 7 Step 9)

Tool name: "artifact.work_order_emit"

Goal:
- Convert BUILD_SPEC into deterministic, self-contained WORK_ORDER JSON.
- Preserve full lineage + hashes.
- Declarative only (NO execution logic).

Hard rules:
- Writes ONLY under .adam_os/artifacts/work_orders/
- Appends ONLY to .adam_os/artifacts/artifact_registry.jsonl
- No system clock reads; created_at_utc must be injected
- Deterministic hashing via canonical_dumps + sha256_hex
- Idempotent behavior
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict

from adam_os.artifacts.registry import ArtifactRegistry, sha256_file, file_size_bytes
from adam_os.memory.canonical import canonical_dumps, sha256_hex


TOOL_NAME = "artifact.work_order_emit"

ARTIFACT_ROOT = Path(".adam_os") / "artifacts"
SPECS_DIR = ARTIFACT_ROOT / "specs"
WORK_ORDERS_DIR = ARTIFACT_ROOT / "work_orders"

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


def artifact_work_order_emit(tool_input: Dict[str, Any]) -> Dict[str, Any]:
    if not isinstance(tool_input, dict):
        raise TypeError("tool_input must be dict")

    created_at_utc = tool_input.get("created_at_utc")
    if not isinstance(created_at_utc, str) or not created_at_utc.strip():
        raise ValueError("tool_input.created_at_utc must be injected")

    build_spec_artifact_id = tool_input.get("build_spec_artifact_id")
    if not isinstance(build_spec_artifact_id, str) or not build_spec_artifact_id.strip():
        raise ValueError("tool_input.build_spec_artifact_id required")
    spec_id = build_spec_artifact_id.strip()

    media_type = tool_input.get("media_type") or DEFAULT_MEDIA_TYPE

    spec_path = SPECS_DIR / f"{spec_id}.json"
    if not spec_path.exists():
        raise FileNotFoundError(f"BUILD_SPEC not found: {spec_path}")

    spec_obj = json.loads(spec_path.read_text(encoding="utf-8"))

    bundle_hash = spec_obj["bundle"]["bundle_hash"]
    prompt_hash = spec_obj["audit"]["prompt_hash"]
    build_spec_sha256 = sha256_file(spec_path)

    work_order_id = tool_input.get("work_order_artifact_id") or f"{spec_id}--work_order"
    if not isinstance(work_order_id, str) or not work_order_id.strip():
        raise ValueError("work_order_artifact_id invalid")
    work_order_id = work_order_id.strip()

    WORK_ORDERS_DIR.mkdir(parents=True, exist_ok=True)
    work_order_path = WORK_ORDERS_DIR / f"{work_order_id}.json"

    reg = ArtifactRegistry(artifact_root=ARTIFACT_ROOT)

    # Idempotency gate
    if work_order_path.exists() and _registry_has(reg.registry_path, work_order_id, "WORK_ORDER"):
        sha = sha256_file(work_order_path)
        size = file_size_bytes(work_order_path)
        return {
            "artifact_id": work_order_id,
            "kind": "WORK_ORDER",
            "work_order_path": str(work_order_path),
            "registry_path": str(reg.registry_path),
            "sha256": sha,
            "byte_size": size,
            "media_type": media_type,
        }

    work_order_obj = {
        "artifact_id": work_order_id,
        "kind": "WORK_ORDER",
        "created_at_utc": created_at_utc,
        "lineage": {
            "build_spec_artifact_id": spec_id,
            "build_spec_sha256": build_spec_sha256,
            "bundle_hash": bundle_hash,
            "prompt_hash": prompt_hash,
        },
        "execution_intent": spec_obj["spec"],
        "constraints": {
            "no_execution": True,
            "declarative_only": True,
            "proxy_required": True,
        },
        "scope_boundaries": {
            "filesystem_writes": "artifact_root_only",
            "no_runtime_resolution": True,
        },
        "open_questions": spec_obj["spec"]["OPEN_QUESTIONS"],
        "notes": "artifact.work_order_emit",
        "tags": ["phase7", "work_order", "declarative"],
    }

    # Deterministic hash
    canon = canonical_dumps(work_order_obj)
    work_order_hash = sha256_hex(canon)

    work_order_obj["work_order_hash"] = work_order_hash

    final_text = canonical_dumps(work_order_obj) + "\n"
    work_order_path.write_text(final_text, encoding="utf-8")

    sha = sha256_file(work_order_path)
    size = file_size_bytes(work_order_path)

    reg.append_from_file(
        artifact_id=work_order_id,
        kind="WORK_ORDER",
        created_at_utc=created_at_utc,
        file_path=work_order_path,
        media_type=media_type,
        parent_artifact_ids=[spec_id],
        notes="artifact.work_order_emit",
        tags=["phase7", "work_order"],
    )

    return {
        "artifact_id": work_order_id,
        "kind": "WORK_ORDER",
        "build_spec_artifact_id": spec_id,
        "work_order_path": str(work_order_path),
        "registry_path": str(reg.registry_path),
        "sha256": sha,
        "byte_size": size,
        "media_type": media_type,
        "work_order_hash": work_order_hash,
    }
