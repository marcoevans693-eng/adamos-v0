================================================================================
SPEC-008A — PROVIDER CONTRACT
AdamOS v0 — Phase 8 (Step 2)
Provider Abstraction + Model Locking (Frozen Rules)
================================================================================

STATUS
------
DRAFT — CONTRACT FREEZE PENDING

POSITION
--------
This specification defines the provider-facing contract for inference calls.
It is subordinate to SPEC-008 and exists to make provider rules versionable.

NON-NEGOTIABLE INVARIANTS
------------------------
- No hidden system prompts.
- No environment-based prompt augmentation.
- No mutable provider settings once frozen.
- No dynamic model selection ("latest", aliases, floating tags).
- No silent retries.
- Append-only evolution (forward patches only).

================================================================================
SECTION 1 — PROVIDER ENUMERATION
================================================================================

ALLOWED PROVIDERS (ENUM)
------------------------
Provider must be one of:
- "openai"
- "anthropic"

No other provider strings permitted.
No dynamic provider injection permitted.

================================================================================
SECTION 2 — MODEL IDENTIFIER LOCKING
================================================================================

RULES
-----
- "model" must be an explicit provider model identifier.
- "model" MUST NOT be:
    - "latest"
    - "default"
    - "auto"
    - any alias indirection
- Model allowlist is defined by policy (see SPEC-008 Section 3) and may be
  instantiated as a separate appendix in future steps.

================================================================================
SECTION 3 — PARAMETER GOVERNANCE
================================================================================

LOCKED PARAMETERS (CONTRACT)
----------------------------
The request MUST explicitly supply:
- temperature
- max_tokens

But these values are NOT free-form:
- They must be accepted by Policy Gate bounds (SPEC-008 Section 3).
- Provider SDK defaults MUST NOT be relied upon.

PROHIBITED BEHAVIOR
-------------------
- Hidden provider defaults that change behavior without explicit request fields.
- Provider-side automatic retries without explicit contract support.

================================================================================
SECTION 4 — PROMPT GOVERNANCE
================================================================================

RULES
-----
- If a "system_prompt" field is used, it must be explicitly present in the request.
- No implicit system prompt injection is permitted.
- No provider-side message rewriting is permitted.

MUTATION RULE
-------------
If provider abstraction mutates the request payload in any way:
    -> Reject.
    -> Emit ledger receipt.
    -> No provider call.

