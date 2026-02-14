================================================================================
SPEC-008D — POLICY MATRIX
AdamOS v0 — Phase 8 (Step 5)
Explicit Model Allowlist + Parameter Ceilings
================================================================================

STATUS
------
DRAFT — CONTRACT FREEZE PENDING

POSITION
--------
This specification formalizes the explicit model allowlist and parameter
ceilings referenced in SPEC-008 Section 3 and SPEC-008A.

All inference requests MUST conform to this matrix.

NON-NEGOTIABLE INVARIANTS
------------------------
- No dynamic model selection.
- No floating model aliases.
- No implicit parameter defaults.
- Bounds must be enforced before provider call.

================================================================================
SECTION 1 — MODEL ALLOWLIST
================================================================================

OPENAI MODELS (PHASE 8 ALLOWED)
--------------------------------
- "gpt-4o"
- "gpt-4.1"
- "gpt-4.1-mini"

ANTHROPIC MODELS (PHASE 8 ALLOWED)
-----------------------------------
- "claude-3-opus"
- "claude-3-sonnet"
- "claude-3-haiku"

If model not listed:
    -> Reject.
    -> Emit ledger receipt.
    -> No provider call.

================================================================================
SECTION 2 — PARAMETER CEILINGS
================================================================================

TEMPERATURE
-----------
- Minimum: 0.0
- Maximum: 1.0
- Must be explicitly supplied.
- No auto-default allowed.

MAX_TOKENS
----------
- Must be > 0.
- Must not exceed provider hard cap.
- Hard cap enforcement must occur in Policy Gate.

================================================================================
SECTION 3 — FUTURE EXPANSION RULE
================================================================================

- Additional models require forward patch.
- No modification of prior entries.
- Deprecated models must remain documented but disallowed via status flag.

