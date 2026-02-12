# Procedure: Phase 6 deterministic proof (double-run) for Memory Read Layer

from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict
from dataclasses import asdict


# Ensure repo root is on sys.path so `import adam_os` works when run as a script.
_REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(_REPO_ROOT))

from adam_os.memory.api.memory_read import memory_read  # noqa: E402


def _stable_json(obj: Any) -> str:
    return json.dumps(obj, sort_keys=True, ensure_ascii=False, separators=(",", ":"))


def _run_once() -> Dict[str, Any]:
    store_path = ".adam_os/memory_stores/test-store.jsonl"
    query = "phase6-proof"
    token_budget = 800
    max_items = 8
    # Explicit deterministic "now" input (ISO 8601 UTC).
    now_utc = datetime(2026, 2, 11, 0, 0, 0, tzinfo=timezone.utc)

    result = memory_read(
        store_paths=[store_path],
        query=query,
        token_budget=token_budget,
        max_items=max_items,
        now_utc=now_utc,
    )

    return {"result": asdict(result)}


def main() -> int:
    out1 = _run_once()
    out2 = _run_once()

    s1 = _stable_json(out1)
    s2 = _stable_json(out2)

    if s1 != s2:
        print("PHASE6_PROOF_FAIL: nondeterministic output detected", file=sys.stderr)
        print("---- run1 ----", file=sys.stderr)
        print(s1, file=sys.stderr)
        print("---- run2 ----", file=sys.stderr)
        print(s2, file=sys.stderr)
        return 1

    print("PHASE6_PROOF_OK: deterministic double-run confirmed")
    print(s1)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
