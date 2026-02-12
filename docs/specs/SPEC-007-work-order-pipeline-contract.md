================================================================================
SPEC-007 — Work Order Pipeline Contract (Phase 7)
Doc-ID: SPEC-007
Project: AdamOS v0
Status: Draft (Phase 7 lock step)
================================================================================

PURPOSE
-------
Phase 7 defines a governed pipeline that converts UNTRUSTED INPUT into a
Bridge-compliant, auditable, spec-shaped WORK ORDER that is safe to hand to a
future governed executor (Capability Proxy is POST-v0 and OUT OF SCOPE here).

This phase does NOT change Phases 1–6. It adds an additive artifact pipeline with
explicit hashing, lineage, and receipts.

DEFINITIONS
-----------
Untrusted Input:
- Any external source: pasted text, notes, file contents, exported docs, etc.

Artifact:
- A stored blob or structured file that participates in the pipeline.
- Every artifact MUST be hashed (sha256) and registered append-only.

Receipt Chain:
- The auditable linkage from RAW → SANITIZED → BUNDLE → SPEC → WORK_ORDER → SNAPSHOT.
- Each step MUST record parent artifact IDs and hashes.

SOT / FOREVER STORAGE AUTHORITY (LOCKED)
----------------------------------------
- Forever Storage Authority / Source of Truth (SOT) = Hostinger VPS.
- Client devices are thin terminals.
- Codespaces is dev/demo only.
- Google Drive is allowed for offsite backup only; it is NOT SOT.

NON-NEGOTIABLES (DO NOT BREAK PHASES 1–6)
-----------------------------------------
- Registry-based tool execution only (Execution Core).
- Append-only stores where specified (memory + receipts + artifact registry).
- Canonical hashing remains the truth mechanism.
- Trust classification remains non-blocking unless explicitly changed by a later spec.
- Every inference run is auditable: inputs, retrieved artifacts, model, prompt hash, outputs.

SCOPE (PHASE 7)
---------------
Phase 7 introduces a pipeline with the following REQUIRED stages:

A) RAW INGEST
   - Store RAW source as a RAW artifact.
   - Compute sha256, byte size, media type.
   - Append to artifact registry.
   - Emit/run receipt references RAW artifact_id + sha256.

B) SANITIZE / NORMALIZE (DETERMINISTIC)
   - Create SANITIZED artifact derived from RAW.
   - MUST produce atomic statements tagged as exactly one:
       SOURCE-BASED
       ASSUMPTION
       QUESTION
   - Sanitization MUST be deterministic (no LLM at this stage).
   - Registry entry MUST link parent RAW artifact_id.

C) CANON RETRIEVAL (DETERMINISTIC)
   - Select canon items deterministically (IDs + hashes).
   - Log selection list and hashes in a saved artifact (or equivalent durable record).
   - Record selection in receipt.

D) CONTEXT BUNDLE ASSEMBLY
   - Create a BUNDLE MANIFEST artifact that explicitly enumerates membership:
       ordered list of artifact_id + sha256 + byte_size + kind
   - Compute and log bundle_hash (hash of canonical manifest).
   - Registry links to parents (sanitized + canon selection artifact(s)).

E) GOVERNED INFERENCE → BUILD SPEC (AUDITABLE)
   - Generate a BUILD SPEC using a frozen template.
   - Output MUST separate:
       SOURCE-BASED vs INFERRED vs ASSUMPTION
       OPEN QUESTIONS
       SOURCE MAP (spec sections → artifact IDs + hashes)
   - MUST log model meta:
       provider, model, temperature, max_tokens
       prompt_hash (canonical)
       bundle_hash
       spec sha256
   - Registry links SPEC to BUNDLE.

F) WORK ORDER EMIT (DECLARATIVE, STOP-GATED)
   - Emit WORK ORDER JSON that is declarative instructions only.
   - MUST include stop gates / required approvals.
   - MUST reference spec_id + spec sha256 + bundle_hash.
   - MUST include an explicit NO EXECUTION clause in AdamOS v0.

G) END-TO-END RECEIPT CHAIN
   - Every stage logs a receipt entry (run ledger) and registry linkage:
       RAW → SANITIZED → BUNDLE → SPEC → WORK_ORDER

H) SNAPSHOT EXPORT (PORTABLE, ENCRYPTED, HASHED, APPEND-ONLY)
   - Must export a single portable snapshot archive containing (at minimum):
       artifacts blobs (raw/sanitized/bundles/specs/work_orders)
       receipts/runs
       canon selection artifacts (if file-based)
       (future) DuckDB if/when added
   - Snapshot MUST be:
       encrypted (user-controlled encryption)
       hashed (integrity)
       append-only (no overwrites; new snapshot per run/interval)
       referenced by a run receipt / ledger entry

ARTIFACT TYPES (REQUIRED)
-------------------------
RAW
SANITIZED
BUNDLE_MANIFEST
BUILD_SPEC
WORK_ORDER
SNAPSHOT_ARCHIVE

ARTIFACT REGISTRY (REQUIRED)
-----------------------------
Artifact registry MUST be append-only JSONL.

Minimum fields:
- artifact_id (stable UUID)
- kind (RAW/SANITIZED/BUNDLE_MANIFEST/BUILD_SPEC/WORK_ORDER/SNAPSHOT_ARCHIVE)
- created_at_utc (MUST be injected; no system clock reads)
- sha256
- byte_size
- media_type
- parent_artifact_ids (array; empty for RAW)
- notes/tags (optional)

DETERMINISM REQUIREMENTS
------------------------
- Hashing MUST use sha256.
- Any “canonical JSON” hashes MUST use the existing canonicalization rules.
- created_at_utc MUST be injected from the runtime boundary (no direct reads of system clock).
- Deterministic steps (sanitize, canon select, bundle manifest) MUST produce stable output
  for identical inputs.

SAFETY REQUIREMENTS
-------------------
- No network access required for deterministic stages.
- Tools MUST be registry-registered and executed through the Execution Core boundary.
- File writes MUST be restricted to the approved artifact root.

OUT OF SCOPE (PHASE 7)
----------------------
- Capability Proxy integration (POST-v0 only).
- Blocking trust enforcement (Phase 4 remains detection-only).
- Autonomous agents / loops.
- “Forever Memory” semantic promotion.

EOF
================================================================================
