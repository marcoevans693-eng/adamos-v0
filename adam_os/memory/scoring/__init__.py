"""
Deterministic scoring for memory read (Phase 6).

This package MUST remain:
- deterministic
- side-effect free
- pure computation (no I/O, no ledger, no store mutation)
"""
from .deterministic_scorer import DeterministicScorer, ScoredRecord

__all__ = ["DeterministicScorer", "ScoredRecord"]
