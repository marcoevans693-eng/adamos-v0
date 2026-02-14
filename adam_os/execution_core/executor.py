# Procedure: Wire Phase 0/5/7/8 executor to explicit tool registry (add inference response/error emitters)
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Protocol

from adam_os.execution_core.errors import ToolNotFoundError, ToolExecutionError
from adam_os.tools import registry as tool_registry

from adam_os.tools.read_only_repo import repo_list_files, repo_read_text
from adam_os.tools.memory_write import memory_write, TOOL_NAME as MEMORY_WRITE_TOOL_NAME
from adam_os.tools.artifact_ingest import artifact_ingest, TOOL_NAME as ARTIFACT_INGEST_TOOL_NAME
from adam_os.tools.artifact_sanitize import artifact_sanitize, TOOL_NAME as ARTIFACT_SANITIZE_TOOL_NAME
from adam_os.tools.artifact_canon_select import artifact_canon_select, TOOL_NAME as ARTIFACT_CANON_SELECT_TOOL_NAME
from adam_os.tools.artifact_bundle_manifest import artifact_bundle_manifest, TOOL_NAME as ARTIFACT_BUNDLE_MANIFEST_TOOL_NAME
from adam_os.tools.artifact_build_spec import artifact_build_spec, TOOL_NAME as ARTIFACT_BUILD_SPEC_TOOL_NAME
from adam_os.tools.artifact_work_order_emit import artifact_work_order_emit, TOOL_NAME as ARTIFACT_WORK_ORDER_TOOL_NAME
from adam_os.tools.artifact_snapshot_export import (
    artifact_snapshot_export,
    TOOL_NAME as ARTIFACT_SNAPSHOT_EXPORT_TOOL_NAME,
)

from adam_os.tools.inference_request_emit import (
    inference_request_emit,
    TOOL_NAME as INFERENCE_REQUEST_EMIT_TOOL_NAME,
)
from adam_os.tools.inference_response_emit import (
    inference_response_emit,
    TOOL_NAME as INFERENCE_RESPONSE_EMIT_TOOL_NAME,
)
from adam_os.tools.inference_error_emit import (
    inference_error_emit,
    TOOL_NAME as INFERENCE_ERROR_EMIT_TOOL_NAME,
)


class Executor(Protocol):
    def execute_tool(self, tool_name: str, tool_input: Dict[str, Any]) -> Any:
        ...


def _ensure_tools_registered() -> None:
    if not tool_registry.has("repo.list_files"):
        tool_registry.register("repo.list_files", repo_list_files)
    if not tool_registry.has("repo.read_text"):
        tool_registry.register("repo.read_text", repo_read_text)
    if not tool_registry.has(MEMORY_WRITE_TOOL_NAME):
        tool_registry.register(MEMORY_WRITE_TOOL_NAME, memory_write)
    if not tool_registry.has(ARTIFACT_INGEST_TOOL_NAME):
        tool_registry.register(ARTIFACT_INGEST_TOOL_NAME, artifact_ingest)
    if not tool_registry.has(ARTIFACT_SANITIZE_TOOL_NAME):
        tool_registry.register(ARTIFACT_SANITIZE_TOOL_NAME, artifact_sanitize)
    if not tool_registry.has(ARTIFACT_CANON_SELECT_TOOL_NAME):
        tool_registry.register(ARTIFACT_CANON_SELECT_TOOL_NAME, artifact_canon_select)
    if not tool_registry.has(ARTIFACT_BUNDLE_MANIFEST_TOOL_NAME):
        tool_registry.register(ARTIFACT_BUNDLE_MANIFEST_TOOL_NAME, artifact_bundle_manifest)
    if not tool_registry.has(ARTIFACT_BUILD_SPEC_TOOL_NAME):
        tool_registry.register(ARTIFACT_BUILD_SPEC_TOOL_NAME, artifact_build_spec)
    if not tool_registry.has(ARTIFACT_WORK_ORDER_TOOL_NAME):
        tool_registry.register(ARTIFACT_WORK_ORDER_TOOL_NAME, artifact_work_order_emit)
    if not tool_registry.has(ARTIFACT_SNAPSHOT_EXPORT_TOOL_NAME):
        tool_registry.register(ARTIFACT_SNAPSHOT_EXPORT_TOOL_NAME, artifact_snapshot_export)
    if not tool_registry.has(INFERENCE_REQUEST_EMIT_TOOL_NAME):
        tool_registry.register(INFERENCE_REQUEST_EMIT_TOOL_NAME, inference_request_emit)
    if not tool_registry.has(INFERENCE_RESPONSE_EMIT_TOOL_NAME):
        tool_registry.register(INFERENCE_RESPONSE_EMIT_TOOL_NAME, inference_response_emit)
    if not tool_registry.has(INFERENCE_ERROR_EMIT_TOOL_NAME):
        tool_registry.register(INFERENCE_ERROR_EMIT_TOOL_NAME, inference_error_emit)


@dataclass
class LocalExecutor:
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
