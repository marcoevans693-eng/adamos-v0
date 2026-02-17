# Procedure: Phase 9 Step 3 proof — live execute + deterministic replay integrity (no provider re-call)
from __future__ import annotations

import json
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Tuple

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT))

from adam_os.execution_core.executor import LocalExecutor  # noqa: E402


@dataclass(frozen=True)
class RegistryHit:
    kind: str
    artifact_id: str
    line_no: int
    raw: Dict[str, Any]


def _read_jsonl(path: Path) -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            rows.append(json.loads(line))
    return rows


def _require(cond: bool, msg: str) -> None:
    if not cond:
        raise AssertionError(msg)


def _registry_path() -> Path:
    p = REPO_ROOT / ".adam_os" / "inference" / "inference_registry.jsonl"
    if not p.exists():
        raise FileNotFoundError(f"missing registry: {p}")
    return p


def _registry_snapshot(registry_path: Path) -> Tuple[int, int]:
    st = registry_path.stat()
    line_count = 0
    with registry_path.open("r", encoding="utf-8") as f:
        for _ in f:
            line_count += 1
    return (line_count, st.st_size)


def _find_hits_for_ids(rows: List[Dict[str, Any]], artifact_ids: List[str]) -> List[RegistryHit]:
    hits: List[RegistryHit] = []
    want = set(artifact_ids)
    for idx, r in enumerate(rows, start=1):
        aid = r.get("artifact_id") or r.get("id") or r.get("result", {}).get("artifact_id") or r.get("result", {}).get("id")
        if not isinstance(aid, str):
            continue
        if aid in want:
            kind = r.get("kind") or r.get("type") or r.get("artifact_kind") or r.get("record_type") or "UNKNOWN"
            hits.append(RegistryHit(kind=str(kind), artifact_id=aid, line_no=idx, raw=r))
    return hits


def _pick_artifact_id(emitted: Any) -> str:
    if not isinstance(emitted, dict):
        return ""
    aid = emitted.get("artifact_id") or emitted.get("id")
    return aid if isinstance(aid, str) else ""


def main() -> None:
    e = LocalExecutor()

    created_at_utc = "2026-02-16T00:00:00Z"
    snapshot_hash = "c" * 64

    # Discover provider cap (no guessing)
    model = "gpt-4.1-mini"
    caps = e.execute_tool(
        "inference.provider_select",
        {"created_at_utc": created_at_utc, "provider": "openai", "model": model},
    )
    provider_max_tokens_cap = caps.get("provider_max_tokens_cap")
    _require(isinstance(provider_max_tokens_cap, int) and provider_max_tokens_cap > 0,
             "provider_max_tokens_cap missing/invalid from inference.provider_select")
    max_tokens = min(128, provider_max_tokens_cap)

    # 1) Emit request
    req_in = {
        "created_at_utc": created_at_utc,
        "snapshot_hash": snapshot_hash,
        "provider": "openai",
        "model": model,
        "temperature": 0.2,
        "max_tokens": max_tokens,
        "provider_max_tokens_cap": provider_max_tokens_cap,
        "system_prompt": "",
        "user_prompt": "Return a single line: OK",
    }
    r_req = e.execute_tool("inference.request_emit", req_in)
    request_id = r_req.get("artifact_id")
    _require(isinstance(request_id, str) and request_id, "request_emit did not return artifact_id")

    # 2) Execute (live call) — tool input key is request_id
    registry_path = _registry_path()
    pre_exec_lines, pre_exec_bytes = _registry_snapshot(registry_path)

    r_exec = e.execute_tool(
        "inference.execute",
        {"created_at_utc": created_at_utc, "request_id": request_id},
    )

    # 3) Extract emitted artifact ids from nested return payload (actual tool contract)
    emitted_receipt = r_exec.get("emitted_receipt")
    receipt_id = _pick_artifact_id(emitted_receipt)
    _require(receipt_id, "execute did not return emitted_receipt.artifact_id")

    response_id = ""
    error_id = ""
    if r_exec.get("ok") is True:
        response_id = _pick_artifact_id(r_exec.get("emitted_response"))
        _require(response_id, "execute ok==True but missing emitted_response.artifact_id")
    else:
        error_id = _pick_artifact_id(r_exec.get("emitted_error"))
        _require(error_id, "execute ok==False but missing emitted_error.artifact_id")

    # 4) Assert registry contains request + (response|error) + receipt
    rows_after_exec = _read_jsonl(registry_path)
    want_ids = [request_id, receipt_id]
    if response_id:
        want_ids.append(response_id)
    if error_id:
        want_ids.append(error_id)

    hits = _find_hits_for_ids(rows_after_exec, want_ids)
    hit_ids = {h.artifact_id for h in hits}
    _require(request_id in hit_ids, "registry missing request entry")
    _require(receipt_id in hit_ids, "registry missing receipt entry")
    if response_id:
        _require(response_id in hit_ids, "registry missing response entry")
    if error_id:
        _require(error_id in hit_ids, "registry missing error entry")

    # 5) Replay — tool input key is receipt_id (NOT receipt_artifact_id)
    pre_replay_lines, pre_replay_bytes = _registry_snapshot(registry_path)

    r_replay = e.execute_tool(
        "inference.replay",
        {"receipt_id": receipt_id},
    )

    # Replay success shape is status == replay_ok
    _require(r_replay.get("status") == "replay_ok", "replay status != replay_ok")
    _require(r_replay.get("receipt_id") == receipt_id, "replay receipt_id mismatch")

    # Strong “no writes” assertion: registry unchanged during replay
    post_replay_lines, post_replay_bytes = _registry_snapshot(registry_path)
    _require(post_replay_lines == pre_replay_lines, "replay appended to inference_registry.jsonl (unexpected)")
    _require(post_replay_bytes == pre_replay_bytes, "replay changed inference_registry.jsonl size (unexpected)")

    out: Dict[str, Any] = {
        "ok": True,
        "created_at_utc": created_at_utc,
        "provider": "openai",
        "model": model,
        "request_id": request_id,
        "response_id": response_id or None,
        "error_id": error_id or None,
        "receipt_id": receipt_id,
        "registry_path": str(registry_path),
        "registry_exec_snapshot": {"lines_before": pre_exec_lines, "bytes_before": pre_exec_bytes},
        "registry_replay_snapshot": {"lines_before": pre_replay_lines, "bytes_before": pre_replay_bytes},
        "execute_result": r_exec,
        "replay_result": r_replay,
    }
    print(json.dumps(out, sort_keys=True, indent=2))


if __name__ == "__main__":
    main()
