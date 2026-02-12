"""
Memory Controller (Phase 6).

Responsibilities (Phase 6 only):
- retrieve candidates (via deterministic readers)
- score deterministically
- assemble a bounded context package within an explicit token budget

Hard rules:
- deterministic
- no autonomy
- no semantic promotion
- no store mutation
- no ledger writes
"""
from .memory_controller import MemoryController, MemoryReadRequest, MemoryReadResult

__all__ = ["MemoryController", "MemoryReadRequest", "MemoryReadResult"]
