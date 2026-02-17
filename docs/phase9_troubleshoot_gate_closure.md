# Phase 9 — Troubleshoot Gate Closure (Sanity Runner)

Date (UTC): 2026-02-17

## What was broken
1) `scripts/phase9_sanity_runner.py` assumed `inference.request_emit` returned a wrapper dict with `ok/request_id/request_path`.
   - In practice, `request_emit` can return an artifact-shaped dict (INFERENCE_REQUEST) depending on tool behavior.

2) Receipt binding verification expected `parent_artifact_ids` to include `"<request_id>--response"`.
   - Actual receipt shape binds via `receipt.result.artifact_id` (e.g. `"<request_id>--response"`).

3) Runner used `rg` (ripgrep) for registry checks; `rg` was not installed in this Codespaces image.

4) Runner default template request used a model rejected by SPEC-008D allowlist, causing:
   - `policy_reject: model not allowlisted by SPEC-008D`

## Fixes applied (orchestration-only)
- Updated sanity runner to:
  - Accept wrapper OR artifact output from `inference.request_emit`
  - Extract request_id robustly
  - Validate receipt binding via `receipt.result.artifact_id` (fallback: parent_artifact_ids if present)
  - Remove `rg` dependency (registry scan uses python/json parsing)
- Updated runner default template id to an allowlisted OpenAI request artifact (gpt-4.1-mini).

## Proofs (IDs + outcomes)
- VERIFY_ONLY request_id:
  96b35dc0e42ee2cbe0438ffe7b170fb45b063cae1d93274fe9852ad0ebc32914

- FULL RUN PASS request_id:
  e7e5f0603316dd6137e6eca3578edf5069a594b093e2b5c969363a2f574e6a4e

Receipt path (exists):
.adam_os/inference/receipts/e7e5f0603316dd6137e6eca3578edf5069a594b093e2b5c969363a2f574e6a4e--receipt.json

## Commits
- 51c6a57 fix(phase9): sanity runner accepts receipt.result binding + remove rg dependency
- 2349c46 fix(phase9): set sanity runner default to allowlisted template request

## Invariants preserved
- No Phase 1–8 contract/schema changes
- No tool refactors
- Append-only behavior preserved
- Policy gate unchanged; runner now uses allowlisted template by default
