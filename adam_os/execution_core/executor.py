# Procedure: Phase 0/5/7 executor wired to explicit tool registry (no magic discovery)
"""
Execution Core Executor

Now wired to an explicit tool registry:
- tool names map to callables (no magic discovery)
- default is still safe-by-default: only registered tools can run

Registered tools:
- Phase 0: repo.list_files, repo.read_text (read-only)
- Phase 5: memory.write (append-only store write; ledger owned by dispatcher)
- Phase 7: artifact.ingest (RAW artifact write + artifact registry append; ledger owned by dispatcher)
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Protocol

from adam_os.execution_core.errors import ToolNotFoundError, ToolExecutionError
from adam_os.tools import registry as tool_registry
from adam_os.tools.read_only_repo import repo_list_files, repo_read_text
from adam_os.tools.memory_write import memory_write, TOOL_NAME as MEMORY_WRITE_TOOL_NAME
from adam_os.tools.artifact_ingest import artifact_ingest, TOOL_NAME as ARTIFACT_INGEST_TOOL_NAME


class Executor(Protocol):
    def execute_tool(self, tool_name: str, tool_input: Dict[str, Any]) -> Any:
        ...


def _ensure_tools_registered() -> None:
    # Idempotent-ish: only register if missing (avoid double-register ValueError)
    if not tool_registry.has("repo.list_files"):
        tool_registry.register("repo.list_files", repo_list_files)
    if not tool_registry.has("repo.read_text"):
        tool_registry.register("repo.read_text", repo_read_text)

    # Phase 5: append-only memory write
    if not tool_registry.has(MEMORY_WRITE_TOOL_NAME):
        tool_registry.register(MEMORY_WRITE_TOOL_NAME, memory_write)

    # Phase 7: RAW artifact ingest + artifact registry append
    if not tool_registry.has(ARTIFACT_INGEST_TOOL_NAME):
        tool_registry.register(ARTIFACT_INGEST_TOOL_NAME, artifact_ingest)


@dataclass
class LocalExecutor:
    """
    Local tool executor (Phase 0+)
    - executes only explicitly registered tools
    - Phase 0 tools are read-only
    - Phase 5 adds governed append-only memory.write (store-only; ledger owned by dispatcher)
    - Phase 7 adds governed artifact.ingest (artifact-only; registry append-only; ledger owned by dispatcher)
    """

    def __post_init__(self) -> None:
        _ensure_tools_registered()

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
