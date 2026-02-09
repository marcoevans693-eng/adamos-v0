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
from adam_os.execution_core.errors import InvalidDispatchRequest, ToolExecutionError, ToolNotFoundError
from adam_os.execution_core.results import ExecutionResult
from adam_os.execution_core.executor import Executor, LocalExecutor


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

    try:
        out = ex.execute_tool(tool_name.strip(), payload)
        ledger.event("tool.result", {"tool_name": tool_name, "ok": True})
        events_written += 1
        ledger.end({"ok": True})
        events_written += 1
        return ExecutionResult(run_id=ledger.run_id, ok=True, output=out, events_written=events_written)
    except ToolNotFoundError as e:
        ledger.event("tool.result", {"tool_name": tool_name, "ok": False, "error": str(e)})
        events_written += 1
        ledger.end({"ok": False})
        events_written += 1
        return ExecutionResult(run_id=ledger.run_id, ok=False, error=str(e), events_written=events_written)
    except Exception as e:
        # Treat anything else as a tool execution failure for now.
        ledger.event("tool.result", {"tool_name": tool_name, "ok": False, "error": str(e)})
        events_written += 1
        ledger.end({"ok": False})
        events_written += 1
        return ExecutionResult(run_id=ledger.run_id, ok=False, error=str(e), events_written=events_written)
