"""
Execution Core Executor

Defines the executor interface used by the dispatcher.
This is intentionally minimal for Phase 0/1 runtime spine.

Tool wiring is deferred to adam_os/tools and adam_os/agents modules.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Optional, Protocol

from adam_os.execution_core.errors import ToolNotFoundError, ToolExecutionError


class Executor(Protocol):
    """
    Minimal executor contract:
    - execute a named tool with an input payload
    - return tool output (JSON-serializable preferred)
    """

    def execute_tool(self, tool_name: str, tool_input: Dict[str, Any]) -> Any:
        ...


@dataclass
class LocalExecutor:
    """
    Placeholder executor.
    For now, this refuses all tools until tool registry/adapters are wired.
    """

    def execute_tool(self, tool_name: str, tool_input: Dict[str, Any]) -> Any:
        raise ToolNotFoundError(f"Tool not wired: {tool_name}")
