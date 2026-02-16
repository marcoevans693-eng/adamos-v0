# Procedure: Snapshot Gate — snapshot-only wrapper for an existing WORK_ORDER (artifact.snapshot_export)
#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

from adam_os.execution_core.executor import LocalExecutor  # noqa: E402


def _nonempty(s: str | None, label: str) -> str:
    if s is None or not str(s).strip():
        raise ValueError(f"{label} must be non-empty")
    return str(s).strip()


def main() -> int:
    ap = argparse.ArgumentParser(
        description="Snapshot Gate: snapshot an existing WORK_ORDER via artifact.snapshot_export (snapshot-only)."
    )
    ap.add_argument(
        "--work-order",
        required=True,
        help="WORK_ORDER artifact_id to snapshot (e.g. ...--build_spec--work_order)",
    )
    ap.add_argument(
        "--created-at-utc",
        required=True,
        help='created_at_utc timestamp (e.g. "2026-02-16T00:00:00Z")',
    )
    ap.add_argument(
        "--passphrase",
        default="",
        help="Optional. If omitted, uses env ADAMOS_SNAPSHOT_PASSPHRASE. Must be non-empty.",
    )
    ap.add_argument(
        "--verify",
        action="store_true",
        help="If set, verify snapshot files exist and show registry tail lines for SNAPSHOT entries.",
    )
    ap.add_argument(
        "--registry-tail",
        type=int,
        default=80,
        help="Lines of registry to show during --verify (default: 80).",
    )
    args = ap.parse_args()

    work_order_id = _nonempty(args.work_order, "work_order")
    created_at_utc = _nonempty(args.created_at_utc, "created_at_utc")

    passphrase = (args.passphrase or os.environ.get("ADAMOS_SNAPSHOT_PASSPHRASE") or "").strip()
    passphrase = _nonempty(passphrase, "encryption_passphrase (pass --passphrase or set ADAMOS_SNAPSHOT_PASSPHRASE)")

    e = LocalExecutor()
    r = e.execute_tool(
        "artifact.snapshot_export",
        {
            "created_at_utc": created_at_utc,
            "work_order_artifact_id": work_order_id,
            "encryption_passphrase": passphrase,
        },
    )

    # Print deterministic keys (be tolerant of minor return-shape drift)
    snapshot_id = r.get("artifact_id") or r.get("snapshot_id")
    manifest_id = r.get("manifest_artifact_id") or r.get("manifest_id") or r.get("manifest")

    print("SNAPSHOT_ARCHIVE:", snapshot_id)
    print("SNAPSHOT_MANIFEST:", manifest_id)
    print("RAW_RETURN_JSON:")
    print(json.dumps(r, indent=2, sort_keys=True))

    if args.verify:
        snap_id = _nonempty(snapshot_id, "snapshot_id from tool return")
        snap_dir = Path(".adam_os") / "artifacts" / "snapshots" / snap_id
        enc_path = snap_dir / "snapshot.enc"
        man_path = snap_dir / "snapshot_manifest.json"

        print("\nVERIFY_FILES:")
        print(f"DIR: {snap_dir}")
        print(f"ENC_EXISTS: {enc_path.exists()} SIZE: {enc_path.stat().st_size if enc_path.exists() else 'NA'}")
        print(f"MAN_EXISTS: {man_path.exists()} SIZE: {man_path.stat().st_size if man_path.exists() else 'NA'}")

        reg = Path(".adam_os") / "artifacts" / "artifact_registry.jsonl"
        print("\nVERIFY_REGISTRY_PATH:", reg)
        if reg.exists():
            tail_n = max(10, int(args.registry_tail))
            lines = reg.read_text(encoding="utf-8").splitlines()
            tail = lines[-tail_n:]
            print(f"REGISTRY_TAIL_LAST_{tail_n}:")
            for ln in tail:
                if '"kind":"SNAPSHOT_' in ln or '"notes":"artifact.snapshot_export"' in ln:
                    print(ln)
        else:
            print("WARN: registry not found at .adam_os/artifacts/artifact_registry.jsonl")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
