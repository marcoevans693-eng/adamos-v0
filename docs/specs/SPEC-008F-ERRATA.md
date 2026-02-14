================================================================================
AdamOS v0 — SPEC-008F-ERRATA
Errata for SPEC-008F Deterministic Replay Proof Contract
================================================================================

STATUS
------
ERRATA — FROZEN (PLANNING)
Append-only clarification. Does not modify SPEC-008F. It corrects presentation
defects introduced during terminal paste instability while preserving intent.

AFFECTED SPEC
-------------
- SPEC-008F-DETERMINISTIC-REPLAY-PROOF-CONTRACT.md

ISSUE 1 — DUPLICATED SENTENCE IN SECTION 1.2
--------------------------------------------
Observed duplication:
- "Given deterministic inputs, the system MUST produce deterministic outcomes in:"
  appears twice consecutively.

CORRECTION
----------
Treat the section as containing the sentence ONCE. No semantic change.

ISSUE 2 — DUPLICATED LEDGER SAFETY BLOCK IN SECTION 3.3
-------------------------------------------------------
Observed duplication:
- The paragraph beginning "If any proof implementation attempts to write raw
  request/response into the ledger..." appears twice, separated by additional
  delimiter lines.

CORRECTION
----------
Treat the block as containing the paragraph ONCE. No semantic change.

CANONICAL READING RULE (FOR SPEC-008F)
--------------------------------------
When interpreting SPEC-008F, duplicated adjacent lines/blocks caused by paste
instability MUST be treated as a single occurrence, preserving the strictest
meaning and intent. No weakening of constraints is permitted.

