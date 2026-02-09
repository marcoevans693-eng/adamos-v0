"""
Tool Registry (Phase 0)

Purpose
- Provide a minimal, explicit map of tool_name -> callable.
- Keep tool wiring centralized and auditable.
- No dynamic imports. No magic discovery.

A tool callable signature:
    fn(tool_input: dict) -> any
"""

from __future__ import annotations

from typing import Any, Callable, Dict

ToolFn = Callable[[Dict[str, Any]], Any]

_REGISTRY: Dict[str, ToolFn] = {}


def register(name: str, fn: ToolFn) -> None:
    if not isinstance(name, str) or not name.strip():
        raise ValueError("tool name must be a non-empty string")
    if name in _REGISTRY:
        raise ValueError(f"tool already registered: {name}")
    _REGISTRY[name] = fn


def get(name: str) -> ToolFn:
    return _REGISTRY[name]


def has(name: str) -> bool:
    return name in _REGISTRY


def list_tools() -> Dict[str, str]:
    # Return name -> doc(first line) for quick introspection
    out: Dict[str, str] = {}
    for k, fn in sorted(_REGISTRY.items()):
        doc = (fn.__doc__ or "").strip().splitlines()
        out[k] = doc[0] if doc else ""
    return out
