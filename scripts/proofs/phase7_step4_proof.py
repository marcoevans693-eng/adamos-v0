"""scripts.proofs.phase7_step4_proof

Proof: Phase 7 Step 4 artifact.ingest tool is registered and functional.

This proof:
- Executes artifact.ingest through LocalExecutor
- Verifies RAW file exists
- Verifies registry appended (line count increases by 1)
"""

from __future__ import annotations

from pathlib import Path

# Ensure repo root is on sys.path so `import adam_os` works when run as a script.
import sys
from pathlib import Path as _Path
sys.path.insert(0, str(_Path(__file__).resolve().parents[2]))

from adam_os.execution_core.executor import LocalExecutor


def count_lines(path: Path) -> int:
    if not path.exists():
        return 0
    return sum(1 for _ in path.open("r", encoding="utf-8"))


def main() -> None:
    ex = LocalExecutor()

    registry_path = Path(".adam_os") / "artifacts" / "artifact_registry.jsonl"
    before = count_lines(registry_path)

    out = ex.execute_tool(
        "artifact.ingest",
        {
            "content": "phase7 step4 proof raw content\n",
            "created_at_utc": "2000-01-01T00:00:00Z",
            "media_type": "text/plain",
        },
    )

    raw_path = Path(out["raw_path"])
    if not raw_path.exists():
        raise SystemExit(f"FAIL: raw file missing: {raw_path}")

    after = count_lines(registry_path)
    if after != before + 1:
        raise SystemExit(f"FAIL: registry expected {before+1} lines, got {after}")

    print("OK: phase7_step4_proof passed")
    print(f"artifact_id={out['artifact_id']}")
    print(f"raw_path={out['raw_path']}")
    print(f"registry_path={out['registry_path']}")
    print(f"before_lines={before} after_lines={after}")


if __name__ == "__main__":
    main()
