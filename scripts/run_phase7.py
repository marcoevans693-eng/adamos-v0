#!/usr/bin/env python3
# Procedure: Deterministic Phase 7 runner (ingest->sanitize->canon->bundle->build_spec->work_order)

from __future__ import annotations

import argparse
from pathlib import Path

from adam_os.execution_core.executor import LocalExecutor


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("input_path")
    ap.add_argument("--created_at_utc", required=True)
    ap.add_argument("--provider", default="openai")
    ap.add_argument("--model", default="gpt-4o-mini")
    ap.add_argument("--temperature", type=float, default=0.0)
    ap.add_argument("--max_tokens", type=int, default=1200)
    ap.add_argument("--encoding", default="utf-8")
    ap.add_argument("--registry_tail", type=int, default=0)
    args = ap.parse_args()

    p = Path(args.input_path)
    if not p.exists():
        raise SystemExit(f"ERROR: input not found: {p}")

    content = p.read_text(encoding=args.encoding, errors="strict").strip()
    if not content:
        raise SystemExit("ERROR: input is empty after strip()")

    e = LocalExecutor()

    r_raw = e.execute_tool("artifact.ingest", {"created_at_utc": args.created_at_utc, "content": content})
    raw_id = r_raw["artifact_id"]
    print("RAW:", raw_id)

    r_san = e.execute_tool("artifact.sanitize", {"created_at_utc": args.created_at_utc, "raw_artifact_id": raw_id})
    san_id = r_san["artifact_id"]
    print("SANITIZED:", san_id)

    r_can = e.execute_tool("artifact.canon_select", {"created_at_utc": args.created_at_utc, "sanitized_artifact_id": san_id})
    can_id = r_can["artifact_id"]
    print("CANON:", can_id)

    r_bun = e.execute_tool("artifact.bundle_manifest", {"created_at_utc": args.created_at_utc, "canon_artifact_id": can_id})
    bun_id = r_bun["artifact_id"]
    print("BUNDLE:", bun_id)

    r_spec = e.execute_tool(
        "artifact.build_spec",
        {
            "created_at_utc": args.created_at_utc,
            "bundle_artifact_id": bun_id,
            "provider": args.provider,
            "model": args.model,
            "temperature": args.temperature,
            "max_tokens": args.max_tokens,
        },
    )
    spec_id = r_spec["artifact_id"]
    print("BUILD_SPEC:", spec_id)

    r_wo = e.execute_tool("artifact.work_order_emit", {"created_at_utc": args.created_at_utc, "build_spec_artifact_id": spec_id})
    wo_id = r_wo["artifact_id"]
    print("WORK_ORDER:", wo_id)

    print("PIPELINE COMPLETE")

    if args.registry_tail and args.registry_tail > 0:
        reg = Path(".adam_os/artifacts/artifact_registry.jsonl")
        if reg.exists():
            lines = reg.read_text(encoding="utf-8").splitlines()
            n = int(args.registry_tail)
            print("---- REGISTRY TAIL ----")
            for line in lines[-n:]:
                print(line)
        else:
            print("WARN: registry not found at .adam_os/artifacts/artifact_registry.jsonl")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
