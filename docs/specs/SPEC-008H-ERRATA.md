================================================================================
AdamOS v0 — SPEC-008H-ERRATA
Errata for SPEC-008H Inference Registry Integration Rules
================================================================================

STATUS
------
ERRATA — FROZEN (PLANNING)
Append-only clarification. Does not modify SPEC-008H. Corrects presentation
defects introduced during terminal paste instability while preserving intent.

AFFECTED SPEC
-------------
- SPEC-008H-INFERENCE-REGISTRY-INTEGRATION.md

ISSUE 1 — DUPLICATED TAIL BLOCKS (SECTIONS 4–6 REPEATED)
--------------------------------------------------------
Observed defect:
- Sections covering "GOVERNANCE: WHAT INFERENCE TOOLS MAY DO" through
  "FORWARD EVOLUTION RULE" appear twice near the end of the file.

CORRECTION
----------
Treat the duplicated repeated tail blocks as a single occurrence. No semantic
change.

CANONICAL READING RULE (FOR SPEC-008H)
--------------------------------------
When interpreting SPEC-008H, duplicated adjacent lines/blocks caused by paste
instability MUST be treated as a single occurrence, preserving the strictest
meaning and intent. No weakening of constraints is permitted.

