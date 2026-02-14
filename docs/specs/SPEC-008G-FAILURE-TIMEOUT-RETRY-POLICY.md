================================================================================
AdamOS v0 — SPEC-008G
Failure, Timeout, Retry Policy (Governed Inference)
================================================================================

STATUS
------
CONTRACT — FROZEN (PLANNING)
No implementation. No code. Defines mandatory failure semantics.

PURPOSE
-------
Define how governed inference behaves under failure conditions: provider errors,
timeouts, partial failures, and retry policy. Enforces "safe failure over autonomy"
and prevents silent retries or hidden recovery behavior.

SCOPE
-----
Applies to:
- inference.request artifacts
- inference.response artifacts
- inference.error artifacts
- inference.receipt ledger entries
- provider calls governed by SPEC-008A
- policy enforcement governed by SPEC-008D
- snapshot binding per SPEC-008E
- determinism boundary per SPEC-008F (+ errata)

NON-GOALS
---------
- No provider-specific implementation details
- No queueing/backoff implementation
- No multi-provider fallback logic (not in v0 unless explicitly added later)

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

DEFINITIONS
-----------
timeout:
  A provider call that fails to complete within the contract-defined duration.

retry:
  A second provider invocation for the same inference.request after a failure.

silent retry:
  Any retry performed without explicit configuration and explicit artifact evidence.

================================================================================
1. FAILURE PRIMITIVES (WHAT CAN GO WRONG)
================================================================================

Failures are classified into these primitives (append-only list):

- invalid_request
- policy_violation
- snapshot_binding_failure
- schema_invalid
- provider_unavailable
- provider_timeout
- provider_rate_limited
- provider_auth_failed
- provider_error
- output_canonicalization_failed
- linkage_invalid
- internal_error

================================================================================
2. TIMEOUT POLICY (MANDATORY)
================================================================================

2.1 Default Timeout (v0)
------------------------
Each inference.request MUST declare a timeout_ms OR inherit a system default
that is explicitly stated and frozen in this spec.

Default timeout_ms (v0): 60000

2.2 Timeout Enforcement
-----------------------
If a provider call exceeds timeout_ms:

- the call MUST be treated as FAILED
- the system MUST emit inference.error with error_type="provider_timeout"
- the system MUST NOT emit inference.receipt
- the system MUST NOT emit inference.response

2.3 No Hidden Extension
-----------------------
The system MUST NOT extend timeout_ms implicitly.
Any change to timeout defaults MUST be append-only and versioned.

================================================================================
3. RETRY POLICY (MANDATORY)
================================================================================

3.1 Default Retry Rule (v0)
---------------------------
Retries are DISALLOWED by default.

- The system MUST NOT retry automatically.
- The system MUST NOT retry silently.
- The system MUST NOT implement fallback to a different provider/model.

3.2 Explicit Retry (Future Append-Only Expansion)
-------------------------------------------------
A future spec MAY introduce explicit retry under strict constraints, but only if:

- retry_count is an explicit request field governed by policy
- every attempt produces artifacts that prove attempt count
- receipts clearly attribute which attempt produced the response
- determinism contract (SPEC-008F) remains satisfied at receipt-level

Until such a spec exists, any retry behavior is NON-COMPLIANT.

================================================================================
4. ERROR ARTIFACT REQUIREMENTS (MANDATORY)
================================================================================

4.1 Uniform Failure Outcome
---------------------------
Any failure MUST produce an inference.error artifact.

Failures MUST NOT produce:
- inference.response artifacts
- inference.receipt ledger entries

Exception:
- If a response artifact was already created but linkage fails later, the system
  MUST still emit inference.error(error_type="linkage_invalid") and MUST NOT
  emit a receipt.

4.2 Required Fields
-------------------
Every inference.error MUST include:

- error_type (from the primitives list in Section 1)
- message (human-readable; no secrets; no raw prompts)
- provider (if known)
- model (if known)
- snapshot_hash (if known)
- snapshot_artifact_id (if known)
- request_artifact_id (if created; else absent/null)

4.3 Error Type Mapping (Minimum)
--------------------------------
- policy_violation -> "policy_violation"
- snapshot binding mismatch/missing -> "snapshot_binding_failure"
- timeout -> "provider_timeout"
- rate limit -> "provider_rate_limited"
- auth failure -> "provider_auth_failed"
- transient provider outage -> "provider_unavailable"
- provider returned error -> "provider_error"
- internal exceptions -> "internal_error"

================================================================================
5. PROVIDER ERROR SURFACING (NO LEAKS)
================================================================================

5.1 No Secret Leakage
---------------------
Error messages MUST NOT include:
- API keys
- authorization headers
- full prompts
- full provider raw outputs

Provider error bodies MAY be summarized, but MUST remain ledger-safe and artifact-safe.

5.2 Where Raw Provider Error May Live
-------------------------------------
If raw provider error payload must be retained for debugging, it MUST be stored
only as an artifact payload (inference.error) and MUST NOT be embedded in the ledger.

================================================================================
6. DETERMINISM IMPLICATIONS
================================================================================

6.1 Replay Classification Stability
-----------------------------------
For deterministic inputs (SPEC-008F), failure classification MUST be stable:

- same request under same policy/snapshot must produce the same error_type
  when rejection occurs before provider call.

6.2 Provider-Nondeterminism Acknowledged
----------------------------------------
Provider-side failures (timeouts, transient errors) may vary between runs and are
NOT required to be stable. When they occur, they must be explicitly classified and
artifact-recorded.

================================================================================
7. FORWARD EVOLUTION RULE (APPEND-ONLY)
================================================================================

Future updates MAY:
- Add new failure primitives (append-only)
- Add explicit, governed retry rules (append-only) with attempt artifacts
- Add per-provider timeout ceilings in the policy matrix (SPEC-008D)

Future updates MUST NOT:
- Introduce silent retries
- Introduce implicit fallback providers/models
- Permit ledger embedding of raw payloads as a recovery mechanism

