# Procedure: Phase 9 Step 5 proof - enforce dispatch boundary (no provider bypass in inference_execute)
from __future__ import annotations

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT))


def _read_text(p: Path) -> str:
    if not p.exists():
        raise SystemExit(f"missing_file: {p}")
    return p.read_text(encoding="utf-8")


def main() -> None:
    p = REPO_ROOT / "adam_os" / "tools" / "inference_execute.py"
    s = _read_text(p)

    # Must route through dispatch_text
    if "from adam_os.providers.dispatch import dispatch_text" not in s:
        raise SystemExit("FAIL: inference_execute must import dispatch_text")

    # Must NOT bypass dispatch directly to OpenAI implementation
    forbidden = [
        "from adam_os.providers.openai_responses import responses_create_text",
        "responses_create_text(",
    ]
    for f in forbidden:
        if f in s:
            raise SystemExit(f"FAIL: forbidden bypass detected in inference_execute: {f}")

    print(
        {
            "ok": True,
            "proof": "phase9_step5_dispatch_guard_proof",
            "checked_file": str(p),
        }
    )


if __name__ == "__main__":
    main()
