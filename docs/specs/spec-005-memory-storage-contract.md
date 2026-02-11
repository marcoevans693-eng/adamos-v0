================================================================================
SPEC-005 — Memory Storage Contract (Append-Only JSONL)
Doc-ID: SPEC-005
Project: AdamOS v0
Status: DRAFT (PHASE 5 DESIGN FREEZE IN PROGRESS)
================================================================================

PURPOSE
-------
Define the canonical storage formats, append-only rules, IDs, timestamps, integrity
hashing, and audit constraints for Phase 5 memory stores.

SCOPE
-----
Applies to v0 file-backed memory stores:
- Episodic (priority)
- Procedural
- Semantic (optional-lite)

NON-NEGOTIABLES
---------------
- Append-only writes (no in-place edits)
- Deterministic load + ordering rules
- Every write produces a memory receipt entry (memory ledger)
- PII handling rules (placeholder policy; no sensitive storage by default)

CANONICAL MEMORY RECORD (V0)
----------------------------
Each memory record is stored as one JSON object per line (JSONL format).

Base Fields (required):

{
  "memory_id": "string (stable, deterministic format)",
  "type": "episodic | procedural | semantic",
  "created_at_utc": "ISO-8601 UTC timestamp",
  "source": "user | system",
  "tags": ["string", "..."],
  "text": "canonical text content",
  "refs": ["optional pointers (run_id, receipt_id, file path)"],
  "hash": "sha256 of canonical fields (excluding hash field)"
}

INTEGRITY RULES
---------------
1. memory_id must be unique within its store.
2. created_at_utc must be UTC only.
3. hash must be computed over a canonical JSON serialization:
   - sorted keys
   - UTF-8 encoding
   - no whitespace variability
4. hash field is written AFTER computing canonical digest.
5. No field deletion permitted once written.

APPEND-ONLY RULES
-----------------
- No in-place file mutation.
- No record deletion in v0.
- Corrections require a new memory record referencing the old memory_id.
- Git history provides immutable historical trace.

STORE FILE LOCATIONS (V0)
-------------------------
Default location (inside repo, deterministic):

adam_os_data/memory/
  episodic.jsonl
  procedural.jsonl
  semantic.jsonl

Notes:
- These are data artifacts, not code.
- Writes are explicit user-approved actions (Phase 5 remains L1 operator).

RETENTION / DELETION (PLACEHOLDER)
----------------------------------
v0: no deletion. Future phases may implement retention windows and redaction rules,
but only via append-only tombstone records plus explicit policy.

EOF
