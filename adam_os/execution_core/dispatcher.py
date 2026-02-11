# Procedure: Dispatcher owns the run boundary + ledger receipts (Phase 3) + trust snapshots (Phase 4)
"""
Execution Core Dispatcher

Owns the run boundary:
- creates run_id
- writes append-only run ledger events
- calls the executor
- returns an ExecutionResult

This is the smallest governed runtime behavior we can implement right now.
"""

from __future__ import annotations

from typing import Any, Dict, Optional

from adam_os.audit.run_ledger import RunLedger
from adam_os.execution_core.errors import InvalidDispatchRequest, ToolNotFoundError
from adam_os.execution_core.results import ExecutionResult
from adam_os.execution_core.executor import Executor, LocalExecutor

# Phase 4 instrumentation (detection-only)
from adam_os.trust.snapshot import collect_snapshot
from adam_os.trust.evaluator import evaluate_trust


def _maybe_emit_memory_write_receipt(
    ledger: RunLedger,
    tool_name: str,
    tool_output: Any,
) -> bool:
    """
    Phase 5: Emit a ledger receipt for successful memory.write ONLY.

    Hard rules:
    - ledger write is owned by dispatcher (not tool)
    - emit only on success
    - never store raw memory content in ledger
    """
    if tool_name != "memory.write":
        return False

    if not isinstance(tool_output, dict):
        return False

    memory_id = tool_output.get("memory_id")
    record_hash = tool_output.get("record_hash")
    store_path = tool_output.get("store_path")

    if not isinstance(memory_id, str) or not memory_id.strip():
        return False
    if not isinstance(record_hash, str) or not record_hash.strip():
        return False
    if not isinstance(store_path, str) or not store_path.strip():
        return False

    ledger.event(
        "memory.write",
        {"memory_id": memory_id, "record_hash": record_hash, "store_path": store_path},
    )
    return True


def dispatch(
    tool_name: str,
    tool_input: Optional[Dict[str, Any]] = None,
    *,
    run_id: Optional[str] = None,
    executor: Optional[Executor] = None,
) -> ExecutionResult:
    if not isinstance(tool_name, str) or not tool_name.strip():
        raise InvalidDispatchRequest("tool_name must be a non-empty string")

    payload = tool_input or {}
    if not isinstance(payload, dict):
        raise InvalidDispatchRequest("tool_input must be a dict (or None)")

    ex = executor or LocalExecutor()
    ledger = RunLedger(run_id=run_id)

    events_written = 0
    ledger.start({"tool_name": tool_name, "tool_input": payload})
    events_written += 1

    # Phase 4: pre-run snapshot
    repo_root = "."
    pre = collect_snapshot(repo_root=repo_root)
    ledger.event("trust.pre_snapshot", pre)
    events_written += 1

    try:
        out = ex.execute_tool(tool_name.strip(), payload)

        # Phase 5: success-only receipts (no raw memory)
        if _maybe_emit_memory_write_receipt(ledger, tool_name.strip(), out):
            events_written += 1

        # Phase 4: post-run snapshot + trust evaluation
        post = collect_snapshot(repo_root=repo_root)
        ledger.event("trust.post_snapshot", post)
        events_written += 1

        status, violations = evaluate_trust(pre, post)
        ledger.event(
            "trust.classification",
            {"status": status, "violations": violations},
        )
        events_written += 1

        ledger.event("tool.result", {"tool_name": tool_name, "ok": True})
        events_written += 1
        ledger.end({"ok": True})
        events_written += 1

        return ExecutionResult(
            run_id=ledger.run_id,
            ok=True,
            output=out,
            events_written=events_written,
        )

    except ToolNotFoundError as e:
        post = collect_snapshot(repo_root=repo_root)
        ledger.event("trust.post_snapshot", post)
        events_written += 1

        status, violations = evaluate_trust(pre, post)
        ledger.event(
            "trust.classification",
            {"status": status, "violations": violations},
        )
        events_written += 1

        ledger.event(
            "tool.result",
            {"tool_name": tool_name, "ok": False, "error": str(e)},
        )
        events_written += 1
        ledger.end({"ok": False})
        events_written += 1

        return ExecutionResult(
            run_id=ledger.run_id,
            ok=False,
            error=str(e),
            events_written=events_written,
        )

    except Exception as e:
        post = collect_snapshot(repo_root=repo_root)
        ledger.event("trust.post_snapshot", post)
        events_written += 1

        status, violations = evaluate_trust(pre, post)
        ledger.event(
            "trust.classification",
            {"status": status, "violations": violations},
        )
        events_written += 1

        ledger.event(
            "tool.result",
            {"tool_name": tool_name, "ok": False, "error": str(e)},
        )
        events_written += 1
        ledger.end({"ok": False})
        events_written += 1

        return ExecutionResult(
            run_id=ledger.run_id,
            ok=False,
            error=str(e),
            events_written=events_written,
        )
