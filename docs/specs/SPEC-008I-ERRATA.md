================================================================================
AdamOS v0 — SPEC-008I-ERRATA
Errata for SPEC-008I Durability Test Matrix (Phase 8 Governed Inference)
================================================================================

STATUS
------
ERRATA — FROZEN (PLANNING)
Append-only clarification. Does not modify SPEC-008I. Corrects presentation and
ordering defects introduced during terminal paste instability while preserving
the intended Phase 8 Step 10 durability requirements.

AFFECTED SPEC
-------------
- SPEC-008I-DURABILITY-TEST-MATRIX.md (commit 09d945d)

SUMMARY OF DEFECTS (OBSERVED)
-----------------------------
D1) Duplicate line in T05:
    "Input: max_tokens too high vs SPEC-008D" appears twice.

D2) Section C (Artifact Schema + Ledger Safety) is truncated / interleaved:
    Content for failure/retry tests (T27/T28) appears inside Section C after T21,
    indicating paste drift and missing test definitions.

D3) Missing tests in canonical numbering (must exist for 30-minimum set):
    T22, T23, T24, T25, T26 are not present as complete test entries in the
    frozen SPEC-008I text as committed.

CANONICAL READING RULE (FOR SPEC-008I)
--------------------------------------
When interpreting Step 10 requirements, use this errata's "CANONICAL MATRIX"
section as the authoritative definition of the minimum required durability set
(T01–T30). SPEC-008I remains the historical frozen artifact, but any drifted,
duplicated, or missing lines must be resolved by this errata without weakening
constraints.

================================================================================
CANONICAL MATRIX (AUTHORITATIVE MINIMUM SET: T01–T30)
================================================================================

A. POLICY GATE + MODEL LOCK (T01–T10)

T01 Reject provider not in enum -> REJECT policy_violation
T02 Reject model alias/"latest" -> REJECT policy_violation
T03 Reject missing model -> REJECT schema_invalid OR policy_violation (implementation must be consistent)
T04 Reject temperature above ceiling -> REJECT policy_violation
T05 Reject max_tokens above ceiling -> REJECT policy_violation
T06 Accept OpenAI locked model within bounds -> ACCEPT; receipt invariants stable
T07 Accept Anthropic locked model within bounds -> ACCEPT; receipt invariants stable
T08 Reject missing system_prompt -> REJECT schema_invalid OR policy_violation (consistent)
T09 Reject system prompt mutation/injection field -> REJECT policy_violation
T10 Reject provider drift attempt (non-enum) -> REJECT policy_violation

B. SNAPSHOT BINDING + CROSS-LINKAGE (T11–T18)

T11 Reject missing snapshot_hash -> REJECT snapshot_missing OR snapshot_binding_failure (consistent)
T12 Reject missing snapshot_artifact_id -> REJECT snapshot_missing OR snapshot_artifact_missing (consistent)
T13 Reject snapshot_artifact_id not found -> REJECT snapshot_artifact_missing
T14 Reject snapshot_hash mismatch vs snapshot artifact -> REJECT snapshot_mismatch
T15 Reject work_order_artifact_id not found (when present) -> REJECT work_order_missing
T16 Reject work_order snapshot mismatch (when present) -> REJECT work_order_mismatch
T17 Accept valid snapshot binding without work_order -> ACCEPT; receipt ok
T18 Accept valid snapshot binding with work_order -> ACCEPT; receipt ok

C. ARTIFACT SCHEMA + LEDGER SAFETY (T19–T24)

T19 Reject invalid request schema -> REJECT schema_invalid
T20 Ledger never stores raw request payload -> ACCEPT; receipt references IDs only
T21 Ledger never stores raw response payload -> ACCEPT; receipt references IDs only
T22 Linkage invalid prevents receipt emission -> REJECT linkage_invalid; no receipt
T23 Response artifact includes snapshot fields -> ACCEPT; response has snapshot_hash + snapshot_artifact_id
T24 Error artifact includes classification fields -> REJECT case; error contains error_type + safe message (+ known attribution fields)

D. FAILURE / TIMEOUT / RETRY (T25–T28)

T25 Provider timeout -> REJECT provider_timeout; no receipt
T26 Provider auth failure -> REJECT provider_auth_failed; no receipt
T27 No retries by default -> REJECT provider_error/provider_unavailable as appropriate; prove single attempt; no silent retry
T28 Rate limiting -> REJECT provider_rate_limited; no receipt

E. REPLAY DETERMINISM (T29–T30)

T29 Double-run reject determinism (policy) -> REJECT both times; error_type stable; attribution fields match
T30 Double-run accept determinism (receipt invariants) -> ACCEPT both times; receipt invariants match; response text may differ

================================================================================
END ERRATA
================================================================================

