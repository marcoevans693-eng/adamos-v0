# Phase 10 — Observability (Engineering Activity Layer)

This phase introduces an append-only engineering activity log for deterministic observability.
All steps are additive and must not modify Phase 1–9 contracts.

Artifacts:
- Runtime log path (untracked): `.adam_os/engineering/activity_log.jsonl`
- Code Shuttle evidence packs (untracked): `_debug/system/*.log`

---

## Step 1 — Standalone Engineering Activity Log Writer (CLOSED)

### Goal
Introduce a deterministic, append-only engineering activity log as instrumentation.
This step is standalone only: it is NOT wired into other tools.

### Implementation
- Writer module: `adam_os/tools/engineering_log_append.py`

### Contract
- Accept structured dict event
- Validate required fields: `created_at_utc`, `event_type`, `status`
- Append exactly ONE JSON line per call (JSONL)
- Deterministic serialization (sorted keys, no whitespace variance)
- Return `sha256` of the exact appended line bytes (including trailing newline)
- No registry writes
- No inference calls
- No background workers / retries

### Proof
- `scripts/proofs/phase10_observability_step1_proof.py`

### Validation Evidence
- `compileall OK`
- Proof appends 1 line per run and verifies:
  - line count increment == 1
  - returned sha256 == sha256(appended bytes including \n)

### Commit
- `feat(obs): add append-only engineering activity log writer + proof`
- Commit: `8ed15fd`

### Status
CLOSED.

---

## Step 2 — Standardized Tool Execution Event Wrapper (CLOSED)

### Goal
Provide a single standardized helper to emit “tool execution” events into the engineering log.
This wrapper is used by Step 3 to instrument tools consistently.

### Implementation
- Wrapper: `adam_os/engineering/activity_events.py`
- Entry point: `log_tool_execution(...)`

### Contract
- Emits one JSONL line per call to the engineering activity log
- Returned value is sha256 of the exact appended bytes (including trailing newline)
- Minimal required fields include:
  - `event_type` == `tool_execute`
  - `tool_name`
  - `status`
  - `request_id`
  - `extra` (caller-provided) must be serialized deterministically

### Proof
- `scripts/proofs/phase10_observability_step2_proof.py`

### Status
CLOSED.

---

## Step 3 — Tool Execution Logging Wired Into Core Tools (CLOSED)

### Goal
Instrument core tools (artifact + inference) to emit standardized tool execution events.
Proofs must validate success + idempotent + error pathways where applicable.

### Instrumented Tools (Step 3 set)
Inference:
- `inference.request_emit`
- `inference.response_emit`
- `inference.execute`

Artifact pipeline:
- `artifact.ingest`
- `artifact.build_spec`
- `artifact.sanitize`
- `artifact.canon_select`
- `artifact.bundle_manifest`
- `artifact.work_order_emit`
- (supporting change) `artifact_snapshot_export` import for log wrapper

### Proofs
- `scripts/proofs/phase10_observability_step3_request_emit_proof.py`
- `scripts/proofs/phase10_observability_step3_response_emit_proof.py`
- `scripts/proofs/phase10_observability_step3_execute_proof.py`
- `scripts/proofs/phase10_observability_step3_artifact_sanitize_proof.py`
- `scripts/proofs/phase10_observability_step3_artifact_canon_select_proof.py`
- `scripts/proofs/phase10_observability_step3_artifact_bundle_manifest_proof.py`
- `scripts/proofs/phase10_observability_step3_artifact_work_order_emit_proof.py`
- `scripts/proofs/phase10_observability_step3_part4_artifact_ingest_proof.py`
- `scripts/proofs/phase10_observability_step3_part4_artifact_build_spec_proof.py`

### Validation Evidence
- `compileall OK`
- All Step 3 proofs green
- Closure evidence pack:
  - `_debug/system/20260218T165724Z_phase10_step3_CLOSURE.log`

### Commits (Step 3 chain)
- `bfe71ca` feat(obs): log engineering events for inference.execute
- `9227e42` feat(obs): log engineering events for inference.response_emit
- `a98fb58` feat(obs): log engineering events for artifact.ingest + proof
- `931caef` feat(obs): log engineering events for artifact.build_spec + proof
- `c18ff00` feat(obs): log artifact.sanitize tool execution + proof
- `c1cdbd1` feat(obs): log artifact.canon_select tool execution + proof
- `c3d7ca2` feat(obs): log artifact.bundle_manifest tool execution + proof
- `b177463` feat(obs): log artifact.work_order_emit tool execution + proof
- `748c4af` feat(obs): add log_tool_execution import to artifact_snapshot_export

### Status
CLOSED.

---

## Code Shuttle v0 (Workflow Hygiene)

Purpose:
- Replace terminal scrollback reasoning with deterministic file artifacts:
  - proof output logs under `_debug/proofs/`
  - operator/codex logs under `_debug/codex/`
  - closure reports under `_debug/system/`

Repo hygiene:
- `_debug/` is ignored via root `.gitignore` to keep the repo clean.
- Commit: `71719dd`
