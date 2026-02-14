================================================================================
AdamOS v0 — SPEC-008H
Inference Tool Registry Integration Rules (Append-Only)
================================================================================

STATUS
------
CONTRACT — FROZEN (PLANNING)
No code. Defines how inference tooling is added without mutating or overwriting
registry behavior.

PURPOSE
-------
Define the rules for registering Phase 8 inference tools into the AdamOS tool
registry while preserving append-only evolution, avoiding silent overwrites, and
maintaining deterministic, auditable tool availability.

SCOPE
-----
Applies to:
- Tool registration surfaces (registry module + executor wiring layer)
- Future tools introduced for Phase 8 inference (request/response/error/receipt)
- Any aliasing or convenience wiring related to inference tools

NON-GOALS
---------
- No implementation details for registry internals
- No runtime dispatch logic
- No changes to frozen Phase 1–7 contracts

REFERENCES (NORMATIVE)
----------------------
- SPEC-008-INFERENCE-SPEC.md
- SPEC-008A-PROVIDER-CONTRACT.md
- SPEC-008B-INFERENCE-ARTIFACT-SCHEMA.md
- SPEC-008C-INFERENCE-LEDGER-INTEGRATION.md
- SPEC-008D-POLICY-MATRIX.md
- SPEC-008E-SNAPSHOT-BINDING-APPENDIX.md
- SPEC-008F-DETERMINISTIC-REPLAY-PROOF-CONTRACT.md (+ ERRATA)
- SPEC-008G-FAILURE-TIMEOUT-RETRY-POLICY.md
- Existing registry + executor invariants established in prior phases

DEFINITIONS
-----------
registry:
  The authoritative tool mapping used by the execution core to resolve tool names
  to implementations.

registration:
  The act of adding a new tool entry (name -> callable) to the registry.

overwrite:
  Any action that replaces an existing registered name with a new implementation.

alias:
  A second name referencing the same implementation as an existing tool.

================================================================================
1. IMMUTABILITY + APPEND-ONLY PRINCIPLE
================================================================================

1.1 No Overwrites
-----------------
A tool name, once registered, MUST NOT be overwritten.

If a registration attempt targets an existing tool name:
- the system MUST reject the registration attempt OR
- the system MUST require an explicit versioned name (see 2.2)

Silent overwrite is forbidden.

1.2 Forward Patches Only
------------------------
New inference tools MUST be added as new names (append-only). Any evolution of a
tool MUST occur via a new versioned name, never by replacing prior behavior.

================================================================================
2. NAMING RULES (DETERMINISTIC + VERSIONABLE)
================================================================================

2.1 Stable Canonical Names
--------------------------
Inference tools MUST use stable, descriptive canonical names.

Recommended base namespace:
- inference.*

Examples:
- inference.request_emit
- inference.run
- inference.response_read
- inference.error_read
- inference.receipt_emit

2.2 Versioned Names for Behavior Changes
----------------------------------------
If a tool’s behavior contract changes (even compatibly), it MUST be released as a
new versioned tool name:

- inference.run.v1
- inference.run.v2

v0 policy: prefer versioned names for any non-trivial semantic changes.

2.3 Alias Rules (Optional, Governed)
------------------------------------
Aliases MAY exist for convenience, but MUST obey:

- alias MUST NOT mask an existing canonical name
- alias MUST be explicitly declared in registry source (no dynamic aliasing)
- alias MUST be removable only via append-only deprecation flags, not deletion

================================================================================
3. REGISTRATION ORDER + DISCOVERY
================================================================================

3.1 Deterministic Registry Assembly
-----------------------------------
Registry assembly MUST be deterministic:

- Given the same codebase snapshot, the same tools MUST be registered in the
  same order and with the same names.
- No environment-dependent tool names.
- No clock-dependent registration behavior.

3.2 No Conditional Tool Presence (v0)
-------------------------------------
Tools MUST NOT appear/disappear based on:
- presence of API keys
- network availability
- provider health

Those conditions affect runtime execution, not registry membership.

================================================================================
4. GOVERNANCE: WHAT INFERENCE TOOLS MAY DO
================================================================================

4.1 Contract Compliance Requirement
-----------------------------------
Any tool registered under inference.* MUST comply with:

- snapshot binding (SPEC-008E)
- provider locking (SPEC-008A)
- policy matrix enforcement (SPEC-008D)
- failure/timeout/retry policy (SPEC-008G)
- ledger safety (SPEC-008C)
- replay determinism boundary (SPEC-008F)

4.2 Ledger Write Scope Restriction
----------------------------------
Inference tools MUST NOT write raw request/response payloads into the run ledger.

Ledger entries, if any, MUST be receipt-only (SPEC-008C).

================================================================================
5. DEPRECATION (APPEND-ONLY, NON-DESTRUCTIVE)
================================================================================

5.1 Deprecation by Flag Only
----------------------------
A tool MAY be deprecated via an explicit metadata flag, but MUST NOT be removed
from registry in v0.

5.2 Deprecation Must Not Break Replay
-------------------------------------
Deprecation MUST NOT break replay attribution for existing artifacts/receipts.
Older tool versions must remain resolvable by name.

================================================================================
6. FORWARD EVOLUTION RULE (APPEND-ONLY)
================================================================================

Future updates MAY:
- Add new inference tool names
- Add stricter naming conventions
- Add registry metadata fields for governance
- Add explicit deprecation metadata (non-destructive)

Future updates MUST NOT:
- Introduce silent overwrites
- Introduce dynamic aliases
- Introduce environment-dependent registry membership

