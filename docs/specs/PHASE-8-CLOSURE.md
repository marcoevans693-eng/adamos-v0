================================================================================
AdamOS v0 — PHASE 8 CLOSURE
Governed Inference Contract Layer
================================================================================

STATUS
------
CLOSED, FROZEN (CODE + SPECS)

This phase establishes the governed inference spine as a deterministic,
fail-closed artifact pipeline with tamper detection and durability proofs.
No provider network calls exist in Phase 8. All outputs are local artifacts.

LOCKED INPUTS
-------------
- Prior phases (1–7) are CLOSED and not modified by Phase 8.
- Snapshot binding is treated as an injected invariant (snapshot_hash input).
- Policy allowlists and ceilings are enforced fail-closed.

PRIMARY OUTCOME (WHY THIS EXISTS)
--------------------------------
Phase 8 turns “inference” into a verifiable chain of custody:

1) A request is emitted deterministically (no SDK calls).
2) A policy gate rejects forbidden configurations before writing.
3) A result is emitted deterministically (response or error).
4) A receipt binds request + result + provider/model + snapshot_hash.
5) Replay recomputes hashes and fails closed on any mismatch.
6) A durability matrix proves success, rejection, and integrity failure behavior.

This is the minimum substrate required before any real provider adapters exist.

ARTIFACT LAYOUT (LOCKED)
------------------------
.adam_os/inference/
  requests/   <request_id>.json
  responses/  <request_id>--response.json
  errors/     <request_id>--error.json
  receipts/   <request_id>--receipt.json
  inference_registry.jsonl   (append-only)

Registry kinds:
- INFERENCE_REQUEST
- INFERENCE_RESPONSE
- INFERENCE_ERROR
- INFERENCE_RECEIPT

IMPLEMENTED TOOLS (LOCKED)
--------------------------
- inference.request_emit
  - Deterministic request artifact emission under .adam_os/inference/requests/
  - Appends INFERENCE_REQUEST to inference_registry.jsonl
  - Idempotent
  - Policy gate enforced fail-closed (SPEC-008D)

- inference.response_emit
  - Deterministic response artifact emission under .adam_os/inference/responses/
  - Appends INFERENCE_RESPONSE
  - Idempotent
  - No provider calls

- inference.error_emit
  - Deterministic error artifact emission under .adam_os/inference/errors/
  - Appends INFERENCE_ERROR
  - Idempotent
  - No provider calls

- inference.provider_select
  - Deterministic provider config selection
  - Injects provider_max_tokens_cap
  - No registry writes

- inference.receipt_emit
  - Deterministic receipt emission under .adam_os/inference/receipts/
  - Binds request_id + request_hash + snapshot_hash + provider/model + result
  - Records inputs_sha256 (request/result file sha256)
  - Computes receipt_hash over canonical receipt payload
  - Appends INFERENCE_RECEIPT
  - Fail-closed on missing referenced artifacts
  - Idempotent

- inference.replay
  - Deterministic verification of an existing receipt
  - Recomputes sha256 for referenced artifacts
  - Recomputes receipt_hash from canonical payload (excluding receipt_hash)
  - Fail-closed on any mismatch
  - No writes, no registry mutation

PROOFS (MUST REMAIN GREEN)
--------------------------
Phase 8 proof files:
- scripts/proofs/phase8_step1_proof.py  (request_emit + registry + idempotency)
- scripts/proofs/phase8_step2_proof.py  (policy gate fail-closed)
- scripts/proofs/phase8_step3_proof.py  (response/error emit + idempotency + registry)
- scripts/proofs/phase8_step5_proof.py  (receipt_emit binds + idempotency)
- scripts/proofs/phase8_step6_proof.py  (replay ok + tamper detection)
- scripts/proofs/phase8_step7_proof.py  (durability matrix: success + rejects + integrity failures)

Durability matrix coverage proven:
A) Success cycle: request_emit -> response_emit -> receipt_emit -> replay OK
B) Policy rejects: non-allowlisted model; max_tokens > provider cap
C) Integrity failures: receipt tamper triggers replay failure; missing artifact triggers fail-closed behavior

SPECS (FROZEN)
--------------
Core Phase 8 specs and appendices:
- SPEC-008-INFERENCE-SPEC.md
- SPEC-008A-PROVIDER-CONTRACT.md
- SPEC-008B-INFERENCE-ARTIFACT-SCHEMA.md
- SPEC-008C-INFERENCE-LEDGER-INTEGRATION.md
- SPEC-008D-POLICY-MATRIX.md
- SPEC-008E-SNAPSHOT-BINDING-APPENDIX.md
- SPEC-008F-DETERMINISTIC-REPLAY-PROOF-CONTRACT.md
- SPEC-008G-FAILURE-TIMEOUT-RETRY-POLICY.md
- SPEC-008H-INFERENCE-REGISTRY-INTEGRATION.md
- SPEC-008I-DURABILITY-TEST-MATRIX.md
Errata (append-only):
- SPEC-008F-ERRATA.md
- SPEC-008H-ERRATA.md
- SPEC-008I-ERRATA.md

NON-GOALS (EXPLICITLY OUT OF SCOPE IN PHASE 8)
----------------------------------------------
- No provider SDK integration
- No network calls
- No real model execution
- No retries/backoff logic beyond policy spec statements
- No ledger integration implementation beyond defined contracts
- No DuckDB integration in Phase 8

INVARIANTS (ENFORCED)
---------------------
- Fail-closed behavior for policy violations and integrity mismatches
- Deterministic canonical JSON writes (sorted keys, stable separators)
- Append-only registry semantics
- Idempotent tool behavior where specified
- Snapshot binding present in request + result + receipt
- Replay is read-only and detects tampering/missing artifacts

CLOSURE CHECKLIST (PASSED)
--------------------------
- compileall OK for adam_os + scripts/proofs
- Phase 8 proofs green:
  - phase8_step1_proof OK
  - phase8_step2_proof OK
  - phase8_step3_proof OK
  - phase8_step5_proof OK
  - phase8_step6_proof OK
  - phase8_step7_proof OK
- Repo clean and synced to origin/main at closure

END
---
PHASE 8 IS CLOSED.
Next work must be defined as a new phase with its own plan/specs and proofs.
================================================================================
