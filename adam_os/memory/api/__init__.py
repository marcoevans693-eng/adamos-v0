"""
Memory API (Phase 6).

Thin, deterministic orchestration layer:
- read candidates from store (JSONL reader)
- map to controller record shape
- score + assemble bounded context via MemoryController

Hard rules:
- deterministic
- no writes, no ledger
- no store mutation
"""
from .memory_read import memory_read

__all__ = ["memory_read"]
