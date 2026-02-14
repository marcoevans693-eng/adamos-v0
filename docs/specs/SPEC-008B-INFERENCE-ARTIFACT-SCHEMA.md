================================================================================
SPEC-008B — INFERENCE ARTIFACT SCHEMA
AdamOS v0 — Phase 8 (Step 3)
Canonical Storage for Inference Inputs/Outputs (Artifact Layer)
================================================================================

STATUS
------
DRAFT — CONTRACT FREEZE PENDING

POSITION
--------
This specification defines how inference data is stored as artifacts.
Ledger receipts MUST reference these artifacts by ID and hash, never embed raw
provider payloads.

NON-NEGOTIABLE INVARIANTS
------------------------
- Artifacts are append-only (new artifacts, never mutation).
- No raw provider payloads in the ledger.
- Deterministic JSON canonicalizable structure.
- Snapshot binding required.

================================================================================
SECTION 1 — ARTIFACT TYPES
================================================================================

TYPES (ENUM)
------------
- "inference.request"
- "inference.response"
- "inference.error"

================================================================================
SECTION 2 — INFERENCE.REQUEST ARTIFACT
================================================================================

CANONICAL STRUCTURE
-------------------
{
  "artifact_type": "inference.request",
  "artifact_id": "<artifact_id>",
  "created_at_utc": "<iso8601>",
  "work_order_id": "<string>",
  "snapshot_hash": "<sha256>",
  "provider": "<enum>",
  "model": "<string>",
  "temperature": "<float>",
  "max_tokens": "<int>",
  "system_prompt": "<string|null>",
  "user_input": "<string>",
  "input_artifact_ids": ["<artifact_id>", "..."]
}

RULES
-----
- system_prompt is optional but must be explicit if present.
- user_input must be explicit (no hidden concatenation).
- input_artifact_ids may be empty but must exist as a field.

================================================================================
SECTION 3 — INFERENCE.RESPONSE ARTIFACT
================================================================================

CANONICAL STRUCTURE
-------------------
{
  "artifact_type": "inference.response",
  "artifact_id": "<artifact_id>",
  "created_at_utc": "<iso8601>",
  "request_artifact_id": "<artifact_id>",
  "work_order_id": "<string>",
  "snapshot_hash": "<sha256>",
  "provider": "<enum>",
  "model": "<string>",
  "output_text": "<string>",
  "usage": {
    "input_tokens": "<int|null>",
    "output_tokens": "<int|null>",
    "total_tokens": "<int|null>"
  }
}

RULES
-----
- output_text is stored in the artifact layer (never in ledger receipt).
- usage fields may be null if provider does not supply them.

================================================================================
SECTION 4 — INFERENCE.ERROR ARTIFACT
================================================================================

CANONICAL STRUCTURE
-------------------
{
  "artifact_type": "inference.error",
  "artifact_id": "<artifact_id>",
  "created_at_utc": "<iso8601>",
  "request_artifact_id": "<artifact_id>",
  "work_order_id": "<string>",
  "snapshot_hash": "<sha256>",
  "provider": "<enum>",
  "model": "<string>",
  "error_type": "<string>",
  "error_message": "<string>"
}

