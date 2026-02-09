"""
Execution Core Errors

Minimal error taxonomy for governed execution.
"""

from __future__ import annotations


class ExecutionCoreError(Exception):
    """Base class for execution core failures."""


class ToolNotFoundError(ExecutionCoreError):
    """Raised when a requested tool cannot be resolved."""


class ToolExecutionError(ExecutionCoreError):
    """Raised when tool invocation fails."""


class InvalidDispatchRequest(ExecutionCoreError):
    """Raised when dispatch inputs are invalid."""
