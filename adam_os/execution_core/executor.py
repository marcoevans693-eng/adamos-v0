"""
Execution Core Executor

Now wired to an explicit tool registry:
- tool names map to callables (no magic discovery)
- default is still safe-by-default: only registered tools can run
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Protocol

from adam_os.execution_core.errors import ToolNotFoundError, ToolExecutionError
from adam_os.tools import registry as tool_registry
from adam_os.tools.read_only_repo import repo_list_files, repo_read_text


class Executor(Protocol):
    def execute_tool(self, tool_name: str, tool_input: Dict[str, Any]) -> Any:
        ...


def _ensure_phase0_tools_registered() -> None:
    # Idempotent-ish: only register if missing (avoid double-register ValueError)
    if not tool_registry.has("repo.list_files"):
        tool_registry.register("repo.list_files", repo_list_files)
    if not tool_registry.has("repo.read_text"):
        tool_registry.register("repo.read_text", repo_read_text)


@dataclass
class LocalExecutor:
    """
    Local tool executor (Phase 0)
    - executes only explicitly registered tools
    - tools are pure/read-only in this phase
    """

    def __post_init__(self) -> None:
        _ensure_phase0_tools_registered()

    def execute_tool(self, tool_name: str, tool_input: Dict[str, Any]) -> Any:
        name = (tool_name or "").strip()
        if not name:
            raise ToolNotFoundError("empty tool name")

        if not tool_registry.has(name):
            raise ToolNotFoundError(f"Tool not wired: {name}")

        fn = tool_registry.get(name)
        try:
            return fn(tool_input)
        except ToolNotFoundError:
            raise
        except Exception as e:
            raise ToolExecutionError(str(e)) from e
