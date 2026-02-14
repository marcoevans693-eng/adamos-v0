================================================================================
AdamOS v0 — SPEC-008F
Deterministic Replay Proof Contract (Receipt-Level)
================================================================================

STATUS
------
CONTRACT — FROZEN (PLANNING)
No implementation. No code. Defines proof obligations and acceptance criteria.

PURPOSE
-------
Define what "deterministic replay" means for Phase 8 Governed Inference and
how it is proven. Determinism is defined at the GOVERNANCE + ATTRIBUTION
boundary (artifacts + receipts), not at model-text output.

SCOPE
-----
Applies to:
- inference.request artifacts
- inference.response artifacts
- inference.error artifacts
- inference.receipt ledger entries
- snapshot binding invariants (SPEC-008E)
- provider/model locking (SPEC-008A)
- policy matrix enforcement (SPEC-008D)
- ledger integration (SPEC-008C)

NON-GOALS
---------
- No claim that LLM text output is bitwise deterministic.
- No requirement that remote providers return identical text across runs.
- No implementation of caching, retry, or replay runners (contract only).

REFERENCES (NORMATIVE)
----------------------
- SPEC-008-INFERENCE-SPEC.md
- SPEC-008A-PROVIDER-CONTRACT.md
- SPEC-008B-INFERENCE-ARTIFACT-SCHEMA.md
- SPEC-008C-INFERENCE-LEDGER-INTEGRATION.md
- SPEC-008D-POLICY-MATRIX.md
- SPEC-008E-SNAPSHOT-BINDING-APPENDIX.md
- Phase 7 Snapshot Artifact Contract(s)

DEFINITIONS
-----------
Replay:
  A second execution attempt using the SAME inference.request artifact payload
  (canonical JSON) and the SAME snapshot binding fields.

Receipt-level determinism:
  For a given request artifact (and policy + snapshot), the governance outcomes
  and attribution references MUST be consistent across runs, within defined bounds.

Attribution boundary:
  The minimal set of fields that must match across runs to prove the system is
  deterministic in its governance and audit semantics.

================================================================================
1. DETERMINISM CLAIM (WHAT IS GUARANTEED)
================================================================================

1.1 Deterministic Inputs
------------------------
A replay proof is defined only when ALL of the following are identical:

- request_artifact payload (canonical JSON) is identical byte-for-byte
  (as defined by canonicalization rules in SPEC-008B)
- snapshot_hash is identical
- snapshot_artifact_id is identical
- policy matrix version / identifier is identical (as referenced by the system)
- provider is identical
- model is identical (locked string)
- governed parameters are identical (temperature, max_tokens, etc.)

If any of the above differ, the attempt is NOT considered a replay under this spec.

1.2 Deterministic Outputs (Governance + Attribution Only)
---------------------------------------------------------
Given deterministic inputs, the system MUST produce deterministic outcomes in:

A) Validation results:
   - schema acceptance/rejection
   - snapshot binding acceptance/rejection
   - policy gate acceptance/rejection

B) Artifact typing + linkage:
   - if accepted, request_artifact_id must reference an inference.request
   - response or error artifact MUST be created according to SPEC-008B
   - snapshot fields MUST be present in response/error

C) Ledger semantics:
   - inference.receipt MUST be emitted only when provider call succeeds and
     linkage validates (per SPEC-008C + SPEC-008E)
   - no raw payloads ever in ledger

1.3 Non-Deterministic Domain (Explicitly Excluded)
--------------------------------------------------
LLM-generated text output is explicitly excluded from determinism guarantees.

The replay proof does NOT require identical response text, tokens, or logprobs.

================================================================================
2. ATTRIBUTION BOUNDARY (FIELDS THAT MUST MATCH)
================================================================================

For two runs R1 and R2 that qualify as a replay (Section 1.1):

2.1 If the request is REJECTED in both runs
-------------------------------------------
Both runs MUST yield inference.error artifacts whose REQUIRED classification fields
match exactly:

- error_type (enum)
- snapshot_hash (if present in request)
- snapshot_artifact_id (if present in request)
- provider
- model

The system MUST NOT emit inference.receipt in either run.

Note: error_artifact_id itself MAY differ across runs. The invariant is the
classification and attribution fields above.

2.2 If the request is ACCEPTED in both runs (provider called)
-------------------------------------------------------------
Both runs MUST yield:

- inference.response artifacts present
- inference.receipt ledger entries present

Receipt-level invariants that MUST match exactly between R1 and R2:

- snapshot_hash
- request_artifact_id (the referenced request artifact must be the SAME artifact)
- provider
- model
- policy_profile_id (or policy reference identifier)
- status = "ok"

Receipt-level fields that MAY differ:

- created_at_utc
- latency_ms
- response_artifact_id (may differ if response is re-emitted)
- any provider metadata fields not declared deterministic by SPEC-008C

2.3 Mixed Outcomes (Reject vs Accept)
-------------------------------------
If R1 rejects and R2 accepts (or vice versa) under deterministic inputs, the system
FAILS the replay determinism contract.

================================================================================
3. REPLAY PROOF PROCEDURE (CONTRACTUAL REQUIREMENTS)
================================================================================

3.1 Proof Test Shape (Minimum)
------------------------------
A replay proof MUST be performed as a paired double-run:

- Run 1: Execute governed inference using a single request artifact (Q)
- Run 2: Execute governed inference again using the SAME request artifact (Q)
- Compare outcomes using the Attribution Boundary rules (Section 2)

3.2 Comparison Rule (Deterministic Verdict)
-------------------------------------------
A replay proof PASSES if and only if:

- both runs qualify as replay attempts (Section 1.1)
- both runs have the SAME accept/reject classification
- the required invariant fields match exactly per Section 2

3.3 Ledger Safety During Proof
------------------------------
The proof procedure MUST NOT require embedding raw payloads into the ledger.

If any proof implementation attempts to write raw request/response into the ledger,
the proof is invalid and the implementation is non-compliant.

================================================================================
4. REQUIRED CASE CLASSES (WHAT MUST BE COVERED)
================================================================================

The Phase 8 durability matrix (Step 10) MUST include replay proofs across these
classes:

A) Policy rejection class:
   - same request -> same policy reject classification (error_type stable)

B) Snapshot mismatch class:
   - same request -> same snapshot reject classification (error_type stable)

C) Provider/model lock class:
   - same request -> same accept/reject depending on allowlist (stable)

D) Schema invalid class:
   - same request -> schema reject stable

E) Successful call class:
   - same request -> accepted both times and receipt invariants stable

================================================================================
5. FORWARD EVOLUTION RULE (APPEND-ONLY)
================================================================================

Future updates MAY:
- Strengthen the attribution boundary by adding more fields that MUST match
- Clarify deterministic input requirements
- Expand required case classes

Future updates MUST NOT:
- Weaken determinism guarantees
- Require bitwise deterministic model outputs
- Permit raw payloads in ledger receipts to "prove" determinism

