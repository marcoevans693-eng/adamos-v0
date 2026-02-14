================================================================================
SPEC-008C — INFERENCE LEDGER INTEGRATION
AdamOS v0 — Phase 8 (Step 4)
Run Ledger Receipts for Inference (No Raw Payloads)
================================================================================

STATUS
------
DRAFT — CONTRACT FREEZE PENDING

POSITION
--------
This specification defines how inference activity is recorded in the existing
Phase 3 Run Ledger as append-only receipts, without embedding raw provider
payloads. It binds ledger entries to inference artifacts (SPEC-008B).

NON-NEGOTIABLE INVARIANTS
------------------------
- Run Ledger remains append-only.
- No raw prompt/response bodies in the ledger.
- Ledger entries reference artifacts by ID and hash only.
- No system clock reads (created_at_utc must be injected).
- Snapshot binding required (Phase 7 snapshot hash).

================================================================================
SECTION 1 — LEDGER ENTRY TYPE
================================================================================

ENTRY TYPE (ENUM)
-----------------
Inference ledger entries MUST use:
- "inference.receipt"

No other inference-related entry types permitted in Phase 8.

================================================================================
SECTION 2 — RECEIPT CONTENT (LEDGER-SAFE)
================================================================================

CANONICAL STRUCTURE
-------------------
{
  "entry_type": "inference.receipt",
  "receipt_id": "<uuid>",
  "request_id": "<uuid>",
  "work_order_id": "<string>",
  "snapshot_hash": "<sha256>",
  "provider": "<enum>",
  "model": "<string>",
  "status": "<enum: rejected|success|error>",
  "reason": "<string>",
  "created_at_utc": "<iso8601>",
  "request_artifact_id": "<artifact_id>",
  "response_artifact_id": "<artifact_id|null>",
  "error_artifact_id": "<artifact_id|null>"
}

RULES
-----
- Exactly one of response_artifact_id or error_artifact_id may be non-null
  when status is not "rejected".
- When status="rejected", both response_artifact_id and error_artifact_id
  MUST be null (rejections do not call provider).


================================================================================
SECTION 3 — ARTIFACT LINKAGE GUARANTEES
================================================================================

REQUIREMENTS
------------
- request_artifact_id MUST exist and be of type "inference.request".
- response_artifact_id MUST be type "inference.response" if present.
- error_artifact_id MUST be type "inference.error" if present.
- snapshot_hash in artifacts MUST match snapshot_hash in ledger receipt.

MISMATCH RULE
-------------
If any linkage is invalid:
    -> Reject.
    -> Emit an error receipt (status="error") with reason="linkage_invalid".
    -> No provider call if invalidity detected pre-call.

================================================================================
SECTION 4 — DETERMINISM BOUNDARY
================================================================================

REPLAY
------
Deterministic replay comparisons are performed over:
- the canonicalized ledger receipt fields
- the artifact IDs and hashes referenced

Provider output text may vary, but must remain attributable via artifacts.

