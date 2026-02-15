"""
Phase 8 Step 6 proof - inference.replay

Proves:
- replay verifies valid receipt
- replay detects tampering
"""

from __future__ import annotations

import json
from pathlib import Path

from adam_os.execution_core.executor import LocalExecutor


def main() -> None:
    e = LocalExecutor()

    receipts_dir = Path(".adam_os") / "inference" / "receipts"
    receipt_files = list(receipts_dir.glob("*.json"))
    assert receipt_files, "no receipt files found for replay proof"

    receipt_id = receipt_files[0].stem

    # Replay should pass
    r = e.execute_tool("inference.replay", {"receipt_id": receipt_id})
    assert r["status"] == "replay_ok"

    # Tamper with receipt file
    receipt_path = receipt_files[0]
    obj = json.loads(receipt_path.read_text(encoding="utf-8"))
    obj["provider"] = "tampered-provider"
    receipt_path.write_text(
        json.dumps(obj, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n",
        encoding="utf-8",
    )

    tamper_detected = False
    try:
        e.execute_tool("inference.replay", {"receipt_id": receipt_id})
    except Exception:
        tamper_detected = True

    assert tamper_detected, "tamper not detected"

    print("phase8_step6_proof OK")


if __name__ == "__main__":
    main()
