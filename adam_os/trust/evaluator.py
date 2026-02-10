# Procedure: paste this ENTIRE file content into adam_os/trust/evaluator.py (full replacement)
"""
Phase 4 — Trust Evaluator

Detection only.
Evaluates declared invariants using pre/post snapshots.
"""

from __future__ import annotations

from typing import Dict, List, Tuple


TRUSTED = "TRUSTED"
TAINTED = "TAINTED"


def evaluate_trust(pre: Dict, post: Dict) -> Tuple[str, List[str]]:
    """
    Returns: (trust_status, violations)

    Rule:
      - TRUSTED only if all invariants hold AND required fields are present.
      - TAINTED if anything is missing or changed.
    """
    violations: List[str] = []

    def req(path: str, val) -> None:
        if val is None or (isinstance(val, str) and not val.strip()):
            violations.append(f"missing_required:{path}")

    # Required fields (critical)
    req("pre.git.branch", pre.get("git", {}).get("branch"))
    req("pre.git.head_commit", pre.get("git", {}).get("head_commit"))
    req("post.git.branch", post.get("git", {}).get("branch"))
    req("post.git.head_commit", post.get("git", {}).get("head_commit"))

    pre_git = pre.get("git", {}) or {}
    post_git = post.get("git", {}) or {}

    # Invariant A: branch unchanged
    if pre_git.get("branch") != post_git.get("branch"):
        violations.append("git.branch_changed")

    # Invariant A: HEAD unchanged
    if pre_git.get("head_commit") != post_git.get("head_commit"):
        violations.append("git.head_changed")

    # Invariant A: working tree must remain clean
    if not bool(pre_git.get("is_clean", False)):
        violations.append("git.pre_not_clean")
    if not bool(post_git.get("is_clean", False)):
        violations.append("git.post_not_clean")

    # Invariant A: no modified/untracked files
    if pre_git.get("modified_files"):
        violations.append("git.pre_modified_files_present")
    if pre_git.get("untracked_files"):
        violations.append("git.pre_untracked_files_present")
    if post_git.get("modified_files"):
        violations.append("git.post_modified_files_present")
    if post_git.get("untracked_files"):
        violations.append("git.post_untracked_files_present")

    status = TRUSTED if not violations else TAINTED
    return status, violations
