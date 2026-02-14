================================================================================
SPEC-008 — INFERENCE SPEC
AdamOS v0 — Phase 8
Governed Inference Contract Layer
================================================================================

STATUS
------
DRAFT — CONTRACT FREEZE PENDING

POSITION
--------
This specification defines the governed inference contract for AdamOS v0.
No inference execution may occur outside this contract.

INVARIANT ALIGNMENT
-------------------
- Append-only evolution.
- No mutation of prior phase artifacts.
- No hidden provider prompts.
- No mutable provider settings once frozen.
- No registry overwrite.
- Snapshot binding required.
- Ledger append-only receipts.
- Forward patches only.

SCOPE (PHASE 8)
---------------
This spec defines:
1) Inference request contract
2) Provider abstraction contract
3) Policy gate contract
4) Snapshot binding rule
5) Ledger receipt contract
6) Replay semantics
7) Failure semantics
8) Durability test requirements

Non-goals:
- No inference engine implementation.
- No provider SDK integration.
- No hashing engine expansion.


================================================================================
SECTION 1 — INFERENCE REQUEST CONTRACT
================================================================================

OBJECTIVE
---------
Define the canonical structure for any inference request entering AdamOS.

REQUIREMENTS
------------
- All requests must be explicit JSON objects.
- No implicit system prompts.
- No hidden parameter injection.
- Model identifier must be explicit.
- Temperature and token limits must be explicit.
- Snapshot hash reference must be present.
- Work order ID must be present.
- created_at_utc must be injected externally (never read system clock).

MANDATORY FIELDS
----------------
{
  "request_id": "<uuid>",
  "work_order_id": "<string>",
  "snapshot_hash": "<sha256>",
  "provider": "<enum>",
  "model": "<string>",
  "temperature": "<float>",
  "max_tokens": "<int>",
  "input_artifact_ids": ["<artifact_id>", "..."],
  "created_at_utc": "<iso8601>"
}

VALIDATION RULE
---------------
If any mandatory field is missing:
    -> Reject before provider call.
    -> Write rejection ledger receipt.
    -> No inference execution.



================================================================================
SECTION 2 — PROVIDER ABSTRACTION CONTRACT
================================================================================

OBJECTIVE
---------
Define how external model providers are referenced without leaking hidden behavior.

PROVIDER ENUMERATION
--------------------
Provider must be one of:

- "openai"
- "anthropic"

No dynamic provider strings allowed.

MODEL LOCKING
-------------
- Model name must be explicit.
- No alias indirection.
- No "latest" or floating tags.
- Versioned identifiers only.

PARAMETER GOVERNANCE
--------------------
- temperature and max_tokens must pass Policy Gate constraints.
- No provider-specific hidden defaults.
- No automatic retries without ledger record.
- No streaming unless explicitly declared in contract (future patch).

PROMPT GOVERNANCE
-----------------
- System prompt must be explicit in request payload.
- No hidden prompt injection.
- No environment-based prompt augmentation.

If provider abstraction layer mutates request:
    -> Reject.
    -> Ledger record required.


================================================================================
SECTION 3 — POLICY GATE CONTRACT
================================================================================

OBJECTIVE
---------
Define pre-inference validation constraints that must pass before any provider call.

ROLE
----
Policy Gate executes BEFORE provider abstraction.
If Policy Gate rejects:
    -> No provider call.
    -> Rejection ledger receipt required.

MODEL ALLOWLIST
---------------
- Only explicitly enumerated models permitted.
- No dynamic model strings.
- No environment-based overrides.

PARAMETER BOUNDS
----------------
temperature:
    - Must be within [0.0, 1.0]
    - Default must NOT be auto-injected.
    - Must be explicitly provided.

max_tokens:
    - Must be > 0
    - Must be <= model-defined maximum
    - Must be explicitly provided.

INPUT SIZE CONTROL
------------------
- input_artifact_ids must resolve to existing artifacts.
- Total token estimate must not exceed policy ceiling.
- No silent truncation allowed.

REJECTION SEMANTICS
-------------------
If any rule fails:
    -> Reject deterministically.
    -> Emit ledger receipt with reason.
    -> No partial execution.


================================================================================
SECTION 4 — SNAPSHOT BINDING RULE
================================================================================

OBJECTIVE
---------
Bind every inference request to a deterministic repository state.

REQUIREMENTS
------------
- snapshot_hash must reference a valid Phase 7 snapshot.
- Snapshot must match the work_order_id.
- Snapshot must exist prior to inference request creation.
- No inference execution without snapshot validation.

IMMUTABILITY
------------
- Snapshot hash cannot be altered after request creation.
- If mismatch detected:
    -> Reject.
    -> Emit ledger receipt.
    -> No provider call.

REPLAY GUARANTEE
----------------
Given:
    - Same snapshot_hash
    - Same request payload
    - Same provider + model
Replay must be attributable and auditable.


================================================================================
SECTION 5 — LEDGER RECEIPT CONTRACT
================================================================================

OBJECTIVE
---------
Define the append-only receipt for any inference attempt (success or rejection).

RULES
-----
- Receipt must be written for every request.
- Receipt must never store raw provider prompt/response bodies.
- Receipt must reference artifacts by ID and hash only.
- Receipt must be deterministic JSON canonicalizable.

MANDATORY FIELDS
----------------
{
  "receipt_id": "<uuid>",
  "request_id": "<uuid>",
  "work_order_id": "<string>",
  "snapshot_hash": "<sha256>",
  "provider": "<enum>",
  "model": "<string>",
  "status": "<enum: rejected|success|error>",
  "reason": "<string>",
  "created_at_utc": "<iso8601>",
  "input_artifact_ids": ["<artifact_id>", "..."],
  "output_artifact_id": "<artifact_id|null>"
}


================================================================================
SECTION 6 — REPLAY SEMANTICS
================================================================================

OBJECTIVE
---------
Define how an inference run is re-attributed and compared over time.

RULES
-----
- Replay does not require identical provider output text.
- Replay MUST preserve:
    - snapshot_hash
    - request payload hash (future)
    - provider + model identifier
    - policy decision outcome
    - ledger receipt structure

ATTRIBUTION
-----------
Replay comparisons are made at the receipt + artifact hash layer.

================================================================================
SECTION 7 — FAILURE & TIMEOUT SEMANTICS
================================================================================

OBJECTIVE
---------
Define what constitutes error, timeout, retry, and abort.

RULES
-----
- No automatic retries unless explicitly declared by policy (future patch).
- Any retry attempt must create its own receipt_id.
- Timeouts must be recorded as status="error" with reason="timeout".
- Partial outputs must not be emitted unless explicitly supported (future patch).

================================================================================
SECTION 8 — DURABILITY TEST REQUIREMENTS
================================================================================

OBJECTIVE
---------
Define the minimum durability proof suite required for Phase 8 closure.

REQUIREMENT
-----------
A minimum of 30 durability tests MUST pass before Phase 8 may be closed.

COVERAGE (MINIMUM)
------------------
- Policy Gate rejection cases (missing fields, invalid bounds)
- Provider allowlist violations
- Model locking violations ("latest", alias forms)
- Snapshot mismatch and missing snapshot cases
- Ledger receipt emission on reject/success/error
- Deterministic rejection behavior across double-run
- Registry immutability (no overwrite)
- Terminal instability resilience (atomic writes validated)

