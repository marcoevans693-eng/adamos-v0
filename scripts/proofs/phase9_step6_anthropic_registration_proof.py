# Procedure: Phase 9 Step 6 proof - anthropic is registered in dispatch; unknown provider fails closed (no network)
from __future__ import annotations

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT))

from adam_os.providers.dispatch import dispatch_text  # noqa: E402


def main() -> None:
    # 1) Unknown provider must fail-closed
    try:
        dispatch_text(
            provider="not-a-provider",
            model="x",
            user_input="hi",
            instructions="sys",
            temperature=0.0,
            max_output_tokens=1,
        )
        raise SystemExit("FAIL: unknown provider did not fail-closed")
    except ValueError as e:
        if "dispatch_text_unsupported_provider" not in str(e):
            raise SystemExit(f"FAIL: wrong error for unknown provider: {e}")

    # 2) Anthropic is registered (static check via module text)
    p = REPO_ROOT / "adam_os" / "providers" / "dispatch.py"
    s = p.read_text(encoding="utf-8")
    if '"anthropic": _call_anthropic_text' not in s:
        raise SystemExit("FAIL: anthropic not registered in _TEXT_DISPATCH")

    print({"ok": True, "proof": "phase9_step6_anthropic_registration_proof"})
