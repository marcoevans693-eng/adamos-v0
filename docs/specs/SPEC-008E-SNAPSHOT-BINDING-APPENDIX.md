================================================================================
AdamOS v0 — SPEC-008E
Snapshot Binding Appendix + Cross-Spec Link Rules
================================================================================

STATUS
------
CONTRACT — FROZEN (PLANNING)
No implementation details. No code. No runtime behavior beyond contract language.

PURPOSE
-------
This appendix formalizes snapshot binding, cross-spec linkage, and rejection
semantics for Phase 8 Governed Inference. It ensures every inference event is
immutably anchored to a Phase 7 snapshot boundary and remains auditable via
artifact references and ledger-safe receipts.

SCOPE
-----
Applies to:
- inference.request artifacts
- inference.response artifacts
- inference.error artifacts
- inference.receipt ledger entries
- Provider calls governed by SPEC-008A
- Policy enforcement governed by SPEC-008D
- Snapshot artifacts produced in Phase 7

NON-GOALS
---------
- No provider implementation details
- No retry logic beyond explicit contract semantics
- No tool registry or runtime wiring rules (handled in later steps)

REFERENCES (NORMATIVE)
----------------------
- SPEC-008-INFERENCE-SPEC.md
- SPEC-008A-PROVIDER-CONTRACT.md
- SPEC-008B-INFERENCE-ARTIFACT-SCHEMA.md
- SPEC-008C-INFERENCE-LEDGER-INTEGRATION.md
- SPEC-008D-POLICY-MATRIX.md
- Phase 7 Snapshot Artifact Contract(s)

DEFINITIONS
-----------
snapshot_hash:
  Canonical sha256 hash identifying the immutable Phase 7 snapshot boundary.

snapshot_artifact_id:
  Artifact ID that resolves to the Phase 7 snapshot artifact carrying snapshot_hash.

work_order_artifact_id (optional in this appendix, but may exist upstream):
  Artifact ID of the Phase 7 work order associated with the snapshot.

request_artifact_id:
  Artifact ID of inference.request.

response_artifact_id:
  Artifact ID of inference.response.

error_artifact_id:
  Artifact ID of inference.error.

receipt:
  Ledger-safe inference.receipt entry that references artifact IDs only (no raw payloads).

NORMATIVE LANGUAGE
------------------
MUST / MUST NOT / SHOULD / MAY are used as described in RFC 2119.

================================================================================
1. SNAPSHOT BINDING INVARIANTS (HARD RULES)
================================================================================

1.1 Required Snapshot Fields (Request-Level)
-------------------------------------------
Every inference.request MUST include:

- snapshot_hash (string, sha256 hex)
- snapshot_artifact_id (string)

If either is missing, the request MUST be REJECTED.

1.2 Snapshot Existence and Resolution
-------------------------------------
On receipt of inference.request, the system MUST verify:

- snapshot_artifact_id resolves to an existing artifact
- resolved snapshot artifact contains snapshot_hash
- snapshot_hash in request EXACTLY matches snapshot_hash in snapshot artifact

If any check fails, the request MUST be REJECTED.

1.3 Snapshot Immutability
-------------------------
snapshot_hash is an immutability anchor.

- The system MUST NOT “fix up” mismatched snapshot_hash values.
- The system MUST NOT fallback to any other snapshot.
- The system MUST NOT proceed under partial linkage.

If mismatch exists, the request MUST be REJECTED.

1.4 Cross-Binding to Phase 7 Work Orders (When Present)
-------------------------------------------------------
If inference.request includes a work_order_artifact_id, the system MUST verify:

- work_order_artifact_id resolves to an existing Phase 7 work order artifact
- that work order artifact references the SAME snapshot_hash
- request.snapshot_hash == work_order.snapshot_hash

If mismatch exists, the request MUST be REJECTED.

================================================================================
2. VALIDATION BOUNDARIES (WHERE REJECTION OCCURS)
================================================================================

Snapshot binding MUST be validated at the following boundaries.

2.1 Boundary A — Tool Entry (Ingress Gate)
-----------------------------------------
At the moment the inference tool receives a request:

MUST validate:
- snapshot_hash present
- snapshot_artifact_id present
- provider + model fields present (per SPEC-008A baseline requirements)
- request is canonical JSON (per SPEC-008 / 008B conventions)

If any fail:
- MUST create inference.error artifact (per SPEC-008B)
- MUST NOT create inference.response
- MUST NOT emit inference.receipt

2.2 Boundary B — Artifact Linkage (Pre-Provider Call)
-----------------------------------------------------
Before any provider invocation:

MUST validate:
- snapshot_artifact_id resolves to snapshot artifact
- request.snapshot_hash matches snapshot artifact snapshot_hash
- optional work_order binding checks (Section 1.4)
- policy gate allows provider/model/parameters (SPEC-008D)

If any fail:
- MUST create inference.error artifact
- MUST NOT call provider
- MUST NOT create inference.response
- MUST NOT emit inference.receipt

2.3 Boundary C — Ledger Receipt Emission (Post-Provider)
--------------------------------------------------------
If provider call succeeds and response artifact is created:

MUST validate linkage consistency:
- receipt.snapshot_hash == request.snapshot_hash
- receipt.request_artifact_id references inference.request
- receipt.response_artifact_id references inference.response
- artifact types match their declared schema

If any fail:
- MUST create inference.error artifact (for linkage failure)
- MUST NOT emit inference.receipt

================================================================================
3. CROSS-SPEC LINK RULES (SOURCE OF TRUTH MATRIX)
================================================================================

3.1 Governance Map
------------------
The following documents are authoritative for the listed concerns.

- SPEC-008:
    Inference request contract, replay semantics (high-level), timeout/failure framing (high-level)

- SPEC-008A:
    Provider enum, model locking rules, prompt governance baseline

- SPEC-008B:
    Artifact schemas: inference.request / inference.response / inference.error
    Canonicalization requirements for artifact payloads

- SPEC-008C:
    Ledger receipt: inference.receipt schema (ledger-safe, references only)
    No raw request/response payloads in ledger

- SPEC-008D:
    Policy matrix: allowlists, parameter ceilings, forward expansion rules

- Phase 7 Snapshot Contracts:
    Snapshot artifact schema + snapshot hash definition
    Work order artifact schema (if used for binding checks)

3.2 Conflict Resolution Rule
---------------------------
If any two specs appear to conflict:

- The STRICTER rule MUST win.
- No interpretation may weaken governance.
- Any future clarification MUST be made by append-only additive amendments.

================================================================================
4. REJECTION SEMANTICS + ERROR TAXONOMY
================================================================================

4.1 Rejection Outcome (Uniform)
-------------------------------
Any REJECTED request MUST produce:

- inference.error artifact (SPEC-008B)
- no inference.response artifact
- no inference.receipt ledger entry

4.2 Error Classification (Required)
-----------------------------------
Every inference.error MUST include:

- error_type (enum; see 4.3)
- message (human-readable, no secrets)
- snapshot_hash (if known)
- snapshot_artifact_id (if provided)
- request_artifact_id (if created prior to rejection; otherwise null/absent)

4.3 error_type Enum (Append-Only)
---------------------------------
The following error_type values are defined:

- policy_violation
- snapshot_missing
- snapshot_artifact_missing
- snapshot_mismatch
- work_order_missing
- work_order_mismatch
- artifact_schema_invalid
- linkage_invalid
- provider_unavailable
- provider_timeout
- provider_error
- output_canonicalization_failed

Forward expansion is allowed ONLY by append-only additions to this list.

================================================================================
5. LINKAGE GUARANTEES (ARTIFACTS + RECEIPTS)
================================================================================

5.1 Artifact Relationship Guarantees
------------------------------------
If a provider call is executed:

- There MUST exist an inference.request artifact (request_artifact_id)
- There MUST exist either:
    - an inference.response artifact OR
    - an inference.error artifact
- Both request and response/error MUST include snapshot_hash + snapshot_artifact_id

5.2 Receipt Relationship Guarantees
-----------------------------------
If and only if provider call succeeded and response artifact exists:

- An inference.receipt MAY be emitted, but only if linkage validates.

receipt MUST include:
- created_at_utc
- snapshot_hash
- request_artifact_id
- response_artifact_id
- provider (enum)
- model (locked string)
- policy_profile_id (or equivalent policy reference)
- latency_ms (optional; if present must be numeric)
- status = "ok"

receipt MUST NOT include:
- raw prompt content
- raw provider output
- full request payload
- full response payload

================================================================================
6. DETERMINISM BOUNDARY (WHAT IS / IS NOT CLAIMED)
================================================================================

6.1 What Is Deterministic Here
------------------------------
This appendix defines determinism for GOVERNANCE + LINKAGE, not model outputs.

Deterministic invariants (MUST hold):
- Snapshot binding validation outcomes for the same artifacts
- Policy decision outcomes for the same request fields under the same policy matrix
- Artifact schema validation outcomes
- Receipt linkage invariants (IDs, snapshot hash, types)

6.2 What Is Not Deterministic Here
----------------------------------
Provider model text output is NOT required to be bitwise deterministic.

Replay determinism is defined later (SPEC-008 Step 7), but MUST at minimum
preserve receipt-level invariants and attribution boundaries.

================================================================================
7. FORWARD EVOLUTION RULE (APPEND-ONLY)
================================================================================

7.1 Allowed Changes
-------------------
Future updates MAY:
- Add new error_type values (append-only)
- Add new linkage checks that strengthen governance
- Add new cross-links or clarifications that do not weaken any invariant

7.2 Forbidden Changes
---------------------
Future updates MUST NOT:
- Remove snapshot requirements
- Relax mismatch rejection semantics
- Allow fallback snapshots or “repair” behaviors
- Allow raw payloads inside ledger receipts

================================================================================
8. MINIMAL EXAMPLES (ILLUSTRATIVE ONLY)
================================================================================

8.1 Valid Request Skeleton
--------------------------
{
  "type": "inference.request",
  "snapshot_hash": "<sha256>",
  "snapshot_artifact_id": "<artifact_id>",
  "provider": "openai|anthropic",
  "model": "<locked-model-id>",
  "system_prompt": "<explicit>",
  "temperature": 0.2,
  "max_tokens": 800,
  "input": { ... }
}

8.2 Snapshot Mismatch Rejection
-------------------------------
If request.snapshot_hash != snapshot_artifact.snapshot_hash:

- emit inference.error(error_type="snapshot_mismatch")
- do not call provider
- no inference.response
- no inference.receipt

