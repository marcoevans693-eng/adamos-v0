================================================================================
SPEC-004 — Token Accounting Contract (AdamOS v0)
================================================================================

STATUS
------
Draft (Phase 1 / Docs-only). Not code. Contract is normative.

SCOPE
-----
This contract defines how AdamOS v0 estimates, records, and audits token usage
for any LLM invocation and any context assembly operation.

This is an ACCOUNTING CONTRACT, not a billing integration.
It defines:
- what MUST be captured
- how it MUST be computed or approximated
- what MUST be stored as immutable facts
- what MAY be inferred as meaning (interpretation)

NON-GOALS
---------
- No provider-specific SDK implementation details
- No UI/dashboard requirements
- No optimization strategies
- No multi-tenant billing logic

DEFINITIONS
-----------
Token:
- A model-dependent unit of text encoding used for input/output measurement.

Input Tokens:
- Tokens consumed by the prompt/context sent to a model.

Output Tokens:
- Tokens produced by the model response.

Total Tokens:
- Input Tokens + Output Tokens.

Context Package:
- The assembled bundle of content delivered to the model (system + developer +
  user + tool + memory excerpts + retrieved snippets + attachments metadata).

Accounting Event:
- An immutable record describing a single token-relevant action.

FACTS VS MEANING (Bridge Constitution)
-------------------------------------
Facts (MUST be stored deterministically):
- raw request/response sizes (bytes)
- token counts when provided by the model/provider
- token estimates (with method + version) when exact counts are unavailable
- timestamps, model identifiers, run identifiers
- hashes of canonical request payload and canonical response payload
- policy decisions and approvals associated with the call

Meaning (MAY be derived later):
- cost interpretation (USD), budgets, “expensive vs cheap”
- blame/attribution narratives (who “wasted” tokens)
- recommendations or “efficiency scores”

CONTRACT OVERVIEW
-----------------
Any component that can change token usage MUST emit Accounting Events.

Primary sources of token usage in AdamOS v0:
1) Ingest → chunking / preprocessing (if LLM used)
2) Memory Controller → retrieval + context assembly (prompt shaping)
3) Model Invocation → LLM request + response
4) Tool Calls that include LLM calls (nested or delegated)

REQUIRED INTERFACES
-------------------

A) TokenAccountingReport (per run)
- run_id: string (unique, deterministic format defined elsewhere)
- started_at: ISO-8601 timestamp
- ended_at: ISO-8601 timestamp
- model: string (provider/model id)
- autonomy_level: string (L1-L5 if applicable)
- policy_profile: string (which policy set governed this run)

- totals:
  - input_tokens: integer | null
  - output_tokens: integer | null
  - total_tokens: integer | null
  - token_source: "provider_exact" | "estimated" | "mixed"
  - estimate_method: string | null
  - estimate_method_version: string | null

- breakdown (ordered list):
  - stage: "context_assembly" | "model_call" | "tool_wrapped_model_call" | "other"
  - component: string (e.g., memory-controller, orchestrator, tool-router)
  - input_tokens: integer | null
  - output_tokens: integer | null
  - total_tokens: integer | null
  - token_source: "provider_exact" | "estimated"
  - notes: string | null

- artifacts:
  - canonical_request_sha256: string | null
  - canonical_response_sha256: string | null
  - context_package_sha256: string | null

B) AccountingEvent (append-only)
Each event MUST include:
- event_id: string (unique)
- run_id: string
- ts: ISO-8601 timestamp
- kind:
  - "context_package_built"
  - "model_request_sent"
  - "model_response_received"
  - "token_estimate_computed"
  - "policy_approval_recorded"
  - "policy_block_recorded"

- model: string | null
- token_fields:
  - input_tokens: integer | null
  - output_tokens: integer | null
  - total_tokens: integer | null
  - token_source: "provider_exact" | "estimated" | null
  - estimate_method: string | null
  - estimate_method_version: string | null

- hashes:
  - payload_sha256: string | null
  - response_sha256: string | null
  - context_sha256: string | null

- provenance:
  - component: string
  - source_file: string | null
  - notes: string | null

TOKEN COUNTING RULES
--------------------
Rule 1 — Prefer provider exact token counts.
If the provider returns official token usage metrics, those MUST be recorded as:
token_source = "provider_exact".

Rule 2 — If exact counts are unavailable, estimates MUST be reproducible.
Any estimate MUST include:
- estimate_method (name)
- estimate_method_version (semantic version)
- the raw bytes length of the measured content (for audit)

Rule 3 — Mixed accounting MUST be explicit.
If some stages are exact and others are estimated, token_source = "mixed" and the
breakdown entries MUST specify their source individually.

Rule 4 — Context package must be hash-addressed.
The final assembled context package MUST have a sha256 recorded so that future
audits can reproduce “what was sent”.

Rule 5 — No silent overwrites.
Accounting artifacts MUST be append-only. Corrections happen via new events,
never by mutating prior records.

FAILURE MODES
-------------
- Missing provider token data: MUST fall back to estimate + record method.
- Corrupted context assembly: MUST abort before model invocation.
- Hash mismatch: MUST flag run as integrity_failed and halt downstream steps.

MINIMUM ACCEPTANCE TESTS (DOCS-ONLY)
------------------------------------
A run is “accounting-complete” if:
- totals are present (exact or estimated)
- breakdown exists with at least: context_assembly + model_call
- at least one hash is recorded (context_package_sha256 recommended)
- token_source is not null at totals level
- estimate method metadata is present if any estimate exists

