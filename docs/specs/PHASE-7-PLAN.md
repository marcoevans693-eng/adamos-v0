================================================================================
AdamOS v0 — PHASE 7 PLAN
“Untrusted Input → Bridge-Compliant Work Order (Auditable)”
================================================================================

STATUS
------
PLANNING LOCK (DOCS-ONLY)
No code changes are authorized until this plan and SPEC-007 are committed.

PHASE 7 DEFINITION (LOCKED)
---------------------------
Phase 7 is NOT “AI writes a spec.”
Phase 7 IS:
Normalize untrusted inputs into a Bridge-compliant, auditable spec-shaped work order
safe to hand to a future governed executor (Capability Proxy is POST-v0 and OUT OF SCOPE).

LOCKED INFRA (FOREVER STORAGE AUTHORITY)
---------------------------------------
SOT = Hostinger VPS.
Codespaces = dev/demo only.
Google Drive = offsite backup only (not SOT).

PRIMARY OUTPUTS (DONE MEANS)
----------------------------
1) RAW artifact stored + hashed + registered
2) SANITIZED artifact stored + hashed + registered + linked to RAW
3) CANON selection list (IDs+hashes) logged deterministically
4) CONTEXT BUNDLE manifest (explicit membership) + bundle_hash logged
5) BUILD SPEC (frozen template) with SOURCE-BASED vs ASSUMPTION vs QUESTION separation
6) WORK ORDER JSON (declarative, stop-gated) referencing artifacts/hashes
7) Receipt chain linking RAW→SANITIZED→BUNDLE→SPEC→WORK_ORDER (hashes + model meta)
8) Snapshot export archive (portable, encrypted, hashed, append-only) referenced by receipt

NON-NEGOTIABLES (DO NOT BREAK PHASES 1–6)
-----------------------------------------
- Registry-based tool execution only.
- Append-only where specified (memory + receipts).
- Canonical hashing remains truth mechanism.
- Trust classification remains non-blocking unless explicitly changed by spec.
- Every inference run is auditable: inputs, retrieved artifacts, model, prompt hash, outputs.

================================================================================
PHASE 7 STEPS (SINGLE OPTION)
================================================================================

STEP 1 — DOCS LOCK (YOU ARE HERE)
---------------------------------
- Add SPEC-007 (Work Order Pipeline Contract)
- Add PHASE-7-PLAN (this doc)

Proof:
- docs-only commit
- python -m compileall -q adam_os && echo "compile OK"
- git status clean

Definitive Validation:
1) Contract Check
2) Determinism Check
3) Audit Check
4) Safety Check
5) Proof Check

--------------------------------------------------------------------------------

STEP 2 — ARTIFACT STORAGE ROOT (DEV SHAPE) + VPS MIRROR INTENT
--------------------------------------------------------------
- Introduce artifact root path concept:
  .adam_os/artifacts/
    raw/
    sanitized/
    bundles/
    specs/
    work_orders/
    snapshots/
- Do NOT migrate SOT here; this is dev layout only.
- Later: mirror identical layout on Hostinger VPS.

Proof:
- directories exist
- no changes to Phases 1–6 behavior

--------------------------------------------------------------------------------

STEP 3 — ARTIFACT REGISTRY (APPEND-ONLY)
----------------------------------------
- Add append-only JSONL registry:
  .adam_os/artifacts/artifact_registry.jsonl
- Every artifact write appends a registry record.
- Every record includes sha256 + byte_size + media_type + parent links.

Proof:
- register two artifacts; verify registry append-only; verify hashes stable

--------------------------------------------------------------------------------

STEP 4 — TOOL: RAW INGEST (STRING-ONLY FIRST)
---------------------------------------------
- Registered tool: artifact_ingest
- Input: raw text content (v0)
- Output: RAW artifact file + registry record + run receipt references

Proof:
- ingest same content twice -> different artifact_id, same sha256

--------------------------------------------------------------------------------

STEP 5 — TOOL: SANITIZE / NORMALIZE (NO LLM)
--------------------------------------------
- Registered tool: artifact_sanitize
- Deterministic rules only
- Output: atomic statements tagged SOURCE-BASED / ASSUMPTION / QUESTION
- Registry links SANITIZED → RAW

Proof:
- sanitize same RAW twice -> identical output + identical sha256

--------------------------------------------------------------------------------

STEP 6 — CANON SELECTION (DETERMINISTIC)
----------------------------------------
- Define canon selection rule (fixed)
- Output canon selection artifact listing artifact_id + sha256
- Logged in receipt

Proof:
- selection stable across runs

--------------------------------------------------------------------------------

STEP 7 — TOOL: CONTEXT BUNDLE BUILD
-----------------------------------
- Registered tool: context_bundle_build
- Output: BUNDLE manifest with explicit membership list + bundle_hash

Proof:
- rebuild bundle -> identical bundle_hash

--------------------------------------------------------------------------------

STEP 8 — TOOL: GOVERNED INFERENCE → BUILD SPEC
----------------------------------------------
- Registered tool: spec_generate
- Frozen template output
- Must include:
  SOURCE-BASED / ASSUMPTIONS / OPEN QUESTIONS / SOURCE MAP
- Must log:
  provider, model, temperature, max_tokens
  prompt_hash
  bundle_hash
  output spec sha256

Proof:
- spec generated + auditable meta + clean repo

--------------------------------------------------------------------------------

STEP 9 — TOOL: WORK ORDER EMIT (DECLARATIVE, STOP-GATED)
--------------------------------------------------------
- Registered tool: work_order_emit
- Output JSON references spec + bundle_hash + hashes
- Explicit NO EXECUTION clause

Proof:
- JSON schema validates
- registry + receipt chain complete

--------------------------------------------------------------------------------

STEP 10 — TOOL: SNAPSHOT EXPORT (PORTABLE, ENCRYPTED, HASHED, APPEND-ONLY)
--------------------------------------------------------------------------
- Registered tool: snapshot_export
- Output snapshot archive includes:
  artifacts/, .adam_os/runs/, canon selection artifacts
  (future) DuckDB
- Must be encrypted + hashed + append-only + receipt referenced

Proof:
- snapshot archive produced, hashed, referenced, never overwritten

================================================================================
STOP CONDITIONS (HARD)
================================================================================
- Working tree dirty when it should be clean
- Any phase regression required
- Sanitizer tries to use LLM
- Inference tries tool calling or broad FS writes
- Missing hashes or missing chain links
- Snapshot overwrites prior snapshot

EOF
================================================================================
