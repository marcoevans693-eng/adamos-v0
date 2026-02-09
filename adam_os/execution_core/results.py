"""
Execution Core Results

Stable result shape for a single run dispatch.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass(frozen=True)
class ExecutionResult:
    run_id: str
    ok: bool
    output: Optional[Any] = None
    error: Optional[str] = None
    events_written: int = 0
    meta: Dict[str, Any] = field(default_factory=dict)
    warnings: List[str] = field(default_factory=list)
