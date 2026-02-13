================================================================================
SPEC-007 — Work Order Pipeline Contract (Phase 7)
AdamOS v0
================================================================================

STATUS
------
LOCKED ON COMMIT.
This spec governs the Phase 7 pipeline that normalizes untrusted input into an
auditable, spec-shaped WORK ORDER safe to hand to a future governed executor.
(Capability Proxy is POST-v0 and OUT OF SCOPE.)

SCOPE
-----
This spec defines:
- The Phase 7 artifact pipeline contracts
- Required tool names (registry-only execution)
- Required artifact registry fields and linkage rules
- Required determinism and audit invariants
- Snapshot export rules (portable + encrypted + hashed + append-only)

NON-GOALS
---------
- No execution of work orders in v0
- No tool-calling agent loops
- No mutation of Phases 1–6 contracts or behavior
- No re-interpretation of closed phases

================================================================================
DEFINITIONS
================================================================================

Artifact Root (DEV SHAPE; Codespaces)
-------------------------------------
.adam_os/artifacts/
  raw/
  sanitized/
  bundles/
  specs/
  work_orders/
  snapshots/
  artifact_registry.jsonl     (append-only)

SOT / Forever Storage Authority
-------------------------------
SOT = Hostinger VPS.
Codespaces = dev/demo only.
Google Drive = offsite backup only (not SOT).

Registry
--------
The append-only artifact registry file:
.adam_os/artifacts/artifact_registry.jsonl

Receipt / Run Ledger
--------------------
The existing run ledger/receipt mechanism from prior phases.
Phase 7 must reference artifact hashes and registry record IDs where applicable.

================================================================================
HARD INVARIANTS (PHASE 7 MUST NOT VIOLATE)
================================================================================

1) Registry-Only Tool Execution
------------------------------
All Phase 7 tools MUST be registered and invoked through the existing registry
mechanism. No direct, ad-hoc execution paths.

2) Append-Only Registry
-----------------------
artifact_registry.jsonl is append-only.
No record overwrites.
No record deletion.
No rewriting the file.

3) Canonical Hashing
--------------------
sha256 is computed over bytes-on-disk (or bytes-streamed) exactly as emitted.
Canonical JSON rules apply where the system defines canonical JSON.

4) Linkage / Lineage
--------------------
Every derived artifact MUST link to its parent(s) by:
- parent_artifact_id
- parent_sha256
and MUST carry forward the receipt chain references required for audit.

5) Filesystem Safety
--------------------
Phase 7 tools MUST write only under:
.adam_os/artifacts/<allowed_subdir>/
and MUST NOT mutate or delete pre-existing artifacts.

================================================================================
PHASE 7 PIPELINE (CONTRACTED OUTPUTS)
================================================================================

Pipeline (Locked)
-----------------
RAW → SANITIZED → CANON → BUNDLE_MANIFEST → BUILD_SPEC → WORK_ORDER → SNAPSHOT_EXPORT

Tool Names (Locked)
-------------------
(These names are the registry keys for execution.)
- artifact_ingest
- artifact_sanitize
- artifact_canon_select
- context_bundle_build
- spec_generate
- work_order_emit
- snapshot_export   (Step 10)

Required High-Level Guarantees
------------------------------
- Deterministic hashing for deterministic transforms
- Idempotency where specified by step proofs
- Audit trail: each stage references upstream hashes + prompt/model meta (where applicable)
- STOP-GATED work order: MUST NOT execute anything

================================================================================
ARTIFACT REGISTRY RECORD (MINIMUM FIELDS)
================================================================================

Every registry record MUST include at least:

- artifact_id               (unique ID)
- created_at_utc            (string; provided by caller/tool; no system clock reads if avoidable)
- artifact_type             (raw | sanitized | canon | bundle_manifest | build_spec | work_order | snapshot)
- relpath                   (relative to repo root; must be under .adam_os/artifacts/)
- sha256                    (sha256 of bytes written for this artifact file)
- byte_size                 (int)
- media_type                (e.g., text/plain, application/json, application/octet-stream)
- parents                   (list of {artifact_id, sha256} records; empty only for RAW roots)
- meta                      (object; tool-specific; must not contain raw secrets)

Append-only rule:
- writing a new artifact always appends a new registry record
- never update an old record to “fix” it

================================================================================
STEP 10 — SNAPSHOT EXPORT CONTRACT
================================================================================

Purpose
-------
Create a portable snapshot archive that can be exported to SOT (Hostinger VPS)
and later verified, without mutating any prior artifacts.

Allowed Writes Only
-------------------
snapshot_export MUST write ONLY under:
.adam_os/artifacts/snapshots/

It MUST NEVER overwrite an existing snapshot file or directory.

Snapshot Inputs (Must Be Included)
----------------------------------
At minimum, snapshot export includes:
- .adam_os/artifacts/          (all Phase 7 artifacts + registry)
- .adam_os/runs/               (run receipts)
- canon selection artifacts     (as already present under artifacts/)
- (future) DuckDB file when introduced (if present, include by rule, not by guess)

Snapshot Output (What is Produced)
----------------------------------
snapshot_export produces:
1) An encrypted archive file (portable artifact)
2) A snapshot manifest JSON (deterministic metadata + hashes)
3) A registry entry referencing the encrypted archive and manifest

Encryption + Hashing + Determinism Rule (Critical)
--------------------------------------------------
Encryption MUST be used, but encryption is commonly non-deterministic
(random IV/salt). Therefore:

- Determinism Check for Step 10 applies to the PLAINTEXT ARCHIVE BYTES
  (the pre-encryption tar stream), NOT the ciphertext.

The tool MUST compute and record BOTH:
- archive_plain_sha256    = sha256 of the plaintext archive stream (tar bytes)
- archive_enc_sha256      = sha256 of the encrypted archive bytes written to disk

Expected behaviors:
- archive_plain_sha256 MUST be stable across repeated exports when inputs are unchanged
- archive_enc_sha256 MAY differ across runs (acceptable) due to encryption randomness
- The manifest MUST record both hashes so verification is possible

No Plaintext Persistence Rule
-----------------------------
The tool MUST NOT leave a plaintext snapshot archive on disk after completion.
Plaintext archive bytes may be streamed through hashing and encryption pipelines,
but only the encrypted archive is stored.

Snapshot Directory Layout
-------------------------
Each snapshot export writes to a new unique directory:

.adam_os/artifacts/snapshots/<snapshot_id>/
  snapshot.enc                      (encrypted archive bytes)
  snapshot_manifest.json             (deterministic manifest)

snapshot_id MUST be unique; the system MUST fail if the directory already exists.

Snapshot Manifest (Minimum Fields)
----------------------------------
snapshot_manifest.json MUST include at least:

- snapshot_id
- created_at_utc
- included_roots              (explicit list of included roots)
- file_count
- total_plain_bytes           (plaintext archive byte size)
- archive_plain_sha256
- archive_enc_sha256
- encryption_scheme           (e.g., "age" or "openssl-aes-256-gcm")
- tool_version                (if available)
- parents                     (references to most recent work_order + spec + bundle hashes)
- notes                       (optional; must not include secrets)

Registry Entry for Snapshot
---------------------------
A registry record MUST be appended for:
- the encrypted archive file (artifact_type = snapshot)
- the manifest JSON (artifact_type = snapshot_manifest)
Both MUST link (parents) to the WORK_ORDER artifact (and/or its sha256) as the
primary parent, preserving lineage.

Stop Conditions (Step 10)
-------------------------
snapshot_export MUST hard-stop if any of the following would occur:
- overwrite any existing snapshot file or directory
- write outside .adam_os/artifacts/snapshots/
- mutate or delete any pre-existing artifact
- append-only registry invariant violated
- missing required hashes in the manifest
- missing parent linkage to the work order chain

================================================================================
PROOF EXPECTATIONS (FOR PHASE 7)
================================================================================

Each step introduces a proof script under scripts/proofs/ and must pass:
- compile gate before commit
- proof script success
- repo clean after push

Step 10 proof MUST verify:
- snapshot directory created
- encrypted archive exists
- manifest exists and contains required fields
- manifest.archive_plain_sha256 matches recomputed plaintext hash (from controlled rebuild)
- registry appended (not overwritten) and includes correct parent linkage
- no pre-existing artifacts modified

