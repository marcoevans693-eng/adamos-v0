================================================================================
AdamOS v0 — SPEC-008I
Durability Test Matrix (Phase 8 Governed Inference)
================================================================================

STATUS
------
CONTRACT — FROZEN (PLANNING)
Defines the minimum required durability test set (30 named tests). No code.

PURPOSE
-------
Provide an explicit, auditable durability test matrix for Phase 8. These cases
prove that governed inference preserves:
- policy enforcement
- snapshot binding
- artifact/receipt linkage integrity
- replay determinism boundaries
- registry immutability
- failure/timeout semantics
- terminal instability resilience via atomic writes + verification discipline

REFERENCES (NORMATIVE)
----------------------
- SPEC-008-INFERENCE-SPEC.md
- SPEC-008A-PROVIDER-CONTRACT.md
- SPEC-008B-INFERENCE-ARTIFACT-SCHEMA.md
- SPEC-008C-INFERENCE-LEDGER-INTEGRATION.md
- SPEC-008D-POLICY-MATRIX.md
- SPEC-008E-SNAPSHOT-BINDING-APPENDIX.md
- SPEC-008F-DETERMINISTIC-REPLAY-PROOF-CONTRACT.md
- SPEC-008F-ERRATA.md
- SPEC-008G-FAILURE-TIMEOUT-RETRY-POLICY.md
- SPEC-008H-INFERENCE-REGISTRY-INTEGRATION.md
- SPEC-008H-ERRATA.md
- Phase 7 snapshot/work order artifact contracts

TEST FORMAT (MANDATORY)
-----------------------
Each test MUST define:
- Test_ID (stable)
- Name
- Preconditions
- Input (request fields / artifacts)
- Steps
- Expected_Artifacts (request/response/error)
- Expected_Ledger (receipt yes/no + invariant fields)
- Expected_Result (ACCEPT | REJECT)
- Expected_Error_Type (if REJECT)
- Determinism_Notes (what must match across replays)

================================================================================
A. POLICY GATE + MODEL LOCK (10 TESTS)
================================================================================

T01
Name: Reject provider not in enum
Preconditions: Policy matrix loaded
Input: provider="openrouter"
Steps: submit request
Expected_Artifacts: inference.error
Expected_Ledger: none
Expected_Result: REJECT
Expected_Error_Type: policy_violation
Determinism_Notes: stable reject classification

T02
Name: Reject model alias / "latest"
Input: model="gpt-5-latest"
Expected_Result: REJECT
Expected_Error_Type: policy_violation
Determinism_Notes: stable

T03
Name: Reject missing model
Input: model absent
Expected_Result: REJECT
Expected_Error_Type: schema_invalid OR policy_violation (must be consistent per implementation)
Determinism_Notes: stable

T04
Name: Reject temperature above ceiling
Input: temperature=9.9
Expected_Result: REJECT
Expected_Error_Type: policy_violation
Determinism_Notes: stable

T05
Name: Reject max_tokens above ceiling
Input: max_tokens too high vs SPEC-008D
Expected_Result: REJECT
Expected_Error_Type: policy_violation
Determinism_Notes: stable

T06
Name: Accept OpenAI locked model within bounds
Input: provider="openai", model="<allowed>", params within bounds
Expected_Result: ACCEPT
Expected_Artifacts: request + response
Expected_Ledger: receipt emitted; snapshot_hash/provider/model/policy_ref/status ok
Determinism_Notes: receipt invariants stable; response text may differ

T07
Name: Accept Anthropic locked model within bounds
Expected_Result: ACCEPT
Determinism_Notes: same as T06

T08
Name: Reject system_prompt missing (prompt governance)
Input: system_prompt absent
Expected_Result: REJECT
Expected_Error_Type: schema_invalid OR policy_violation (must be consistent)
Determinism_Notes: stable

T09
Name: Reject prompt injection attempt via dynamic system prompt mutation field
Input: includes forbidden mutation field (per SPEC-008A)
Expected_Result: REJECT
Expected_Error_Type: policy_violation
Determinism_Notes: stable

T10
Name: Reject dynamic provider field / provider drift attempt
Input: provider field includes non-enum variation
Expected_Result: REJECT
Expected_Error_Type: policy_violation
Determinism_Notes: stable

================================================================================
B. SNAPSHOT BINDING + CROSS-LINKAGE (8 TESTS)
================================================================================

T11
Name: Reject missing snapshot_hash
Input: snapshot_hash absent
Expected_Result: REJECT
Expected_Error_Type: snapshot_missing OR snapshot_binding_failure (must be consistent)
Determinism_Notes: stable

T12
Name: Reject missing snapshot_artifact_id
Input: snapshot_artifact_id absent
Expected_Result: REJECT
Expected_Error_Type: snapshot_missing OR snapshot_artifact_missing (must be consistent)
Determinism_Notes: stable

T13
Name: Reject snapshot_artifact_id not found
Input: snapshot_artifact_id points to non-existent artifact
Expected_Result: REJECT
Expected_Error_Type: snapshot_artifact_missing
Determinism_Notes: stable

T14
Name: Reject snapshot_hash mismatch vs snapshot artifact
Input: snapshot_hash != resolved snapshot artifact hash
Expected_Result: REJECT
Expected_Error_Type: snapshot_mismatch
Determinism_Notes: stable

T15
Name: Reject work_order_artifact_id not found (when present)
Input: work_order_artifact_id provided but missing
Expected_Result: REJECT
Expected_Error_Type: work_order_missing
Determinism_Notes: stable

T16
Name: Reject work_order snapshot mismatch (when present)
Input: work_order.snapshot_hash != request.snapshot_hash
Expected_Result: REJECT
Expected_Error_Type: work_order_mismatch
Determinism_Notes: stable

T17
Name: Accept valid snapshot binding without work_order_artifact_id
Input: snapshot_hash + snapshot_artifact_id valid; work_order omitted
Expected_Result: ACCEPT
Expected_Ledger: receipt ok
Determinism_Notes: receipt invariants stable

T18
Name: Accept valid snapshot binding with work_order_artifact_id
Input: snapshot + work_order both valid and consistent
Expected_Result: ACCEPT
Expected_Ledger: receipt ok
Determinism_Notes: receipt invariants stable

================================================================================
C. ARTIFACT SCHEMA + LEDGER SAFETY (6 TESTS)
================================================================================

T19
Name: Reject invalid request schema (missing required fields)
Expected_Result: REJECT
Expected_Error_Type: schema_invalid
Determinism_Notes: stable

T20
Name: Ensure ledger never stores raw request payload
Steps: run ACCEPT flow; inspect ledger receipt structure
Expected_Result: ACCEPT
Expected_Ledger: receipt references only artifact IDs; no raw payloads
Determinism_Notes: stable

T21
Name: Ensure ledger never stores raw response payload
Steps: run ACCEPT flow; inspect ledger receipt structure
Expected_Result: ACCEPT
Expected_Ledger: receipt references only artifact IDs; no raw payloads
Determinism_Notes: stable

T22
Name: Linkage invalid prevents receipt emission
Preconditions: force linkage failure post-response artifact (synthetic)
Expected_Result: REJECT (or ACCEPT without receipt depending on implementation; must conform to SPEC-008E Boundary C)
Expected_Error_Type: linkage_invalid
Expected_Ledger: none
Determinism_Notes: stable

T23
Name: Response artifact must include snapshot fields
Steps: run ACCEPT flow; inspect response artifact schema
Expected_Result: ACCEPT
Expected_Artifacts: response contains snapshot_hash + snapshot_artifact_id
Determinism_Notes: stable

T24
Name: Error artifact must include classification fields
Steps: run known REJECT case; inspect error artifact schema
Expected_Result: REJECT
Expected_Artifacts: error includes error_type + safe message + snapshot/provider/model if known
Determinism_Notes: stable

================================================================================
D. FAILURE / TIMEOUT / RETRY (4 TESTS)
================================================================================

T25
Name: Provider timeout produces provider_timeout error; no receipt
Preconditions: induce timeout > timeout_ms
Expected_Result: REJECT
Expected_Error_Type: provider_timeout
Expected_Ledger: none
Determinism_Notes: provider failures may vary, but classification must be correct when it occurs

T26
Name: Provider auth failure produces provider_auth_failed; no receipt
Expected_Result: REJECT
Expected_Error_Type: provider_auth_failed
Expected_Ledger: none
Determinism_Notes: correct classification

T27
Name: No retries by default (prove single attempt)
Steps: induce transient provider_error; confirm no retry attempts recorded
Expected_Result: REJECT
Expected_Error_Type: provider_error OR provider_unavailable (as appropriate)
Expected_Ledger: none
Determinism_Notes: no silent retry

T28
Name: Rate limiting classified as provider_rate_limited; no receipt
Expected_Result: REJECT
Expected_Error_Type: provider_rate_limited
Expected_Ledger: none
Determinism_Notes: correct classification

================================================================================
E. REPLAY DETERMINISM (2 TESTS)
================================================================================

T29
Name: Double-run reject determinism (policy)
Steps: Run same invalid request twice (same request artifact)
Expected_Result: REJECT both times
Expected_Error_Type: policy_violation (stable)
Determinism_Notes: error_type/provider/model/snapshot fields must match

T30
Name: Double-run accept determinism (receipt invariants)
Steps: Run same valid request twice (same request artifact)
Expected_Result: ACCEPT both times
Expected_Ledger: receipts present; invariants match:
  - snapshot_hash
  - request_artifact_id
  - provider
  - model
  - policy_ref
  - status="ok"
Determinism_Notes: response text may differ; response_artifact_id may differ

================================================================================
F. REGISTRY IMMUTABILITY + TERMINAL RESILIENCE (2 TESTS)
================================================================================

T31
Name: Registry overwrite attempt rejected
Steps: attempt to re-register existing tool name with different impl
Expected_Result: REJECT (registration failure)
Expected_Error_Type: internal_error OR policy_violation (must be consistent)
Determinism_Notes: stable

T32
Name: Terminal atomic-write discipline proof (docs)
Steps: create a spec file via atomic write; verify via wc/sed/tail/grep; commit
Expected_Result: PASS (process compliance)
Determinism_Notes: N/A (process test)

================================================================================
MINIMUM REQUIREMENT
================================================================================
The minimum required durability set is T01–T30. T31–T32 are recommended
extensions. If only 30 are implemented, prioritize T01–T30.

