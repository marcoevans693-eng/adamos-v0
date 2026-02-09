================================================================================
SPEC-003 — Memory Controller Contract
Doc-ID: SPEC-003
Project: AdamOS v0
Status: Draft
================================================================================

PURPOSE
-------
Define the Phase 1 contract for the Memory Controller. The Memory Controller is
the sole authority responsible for retrieving candidate memories and assembling
a bounded context package for downstream model interaction.

In Phase 1, the Memory Controller provides deterministic retrieval, scoring, and
assembly only. No autonomy, no agent behavior, no semantic promotion, and no
Forever Memory implementation are permitted.

DEFINITION
----------
Memory Controller: A governed control-plane component that:
1) Retrieves candidate items from approved stores
2) Scores relevance deterministically
3) Assembles a context package within an explicit token budget
4) Produces an auditable assembly record

The Memory Controller governs context assembly. Nothing else may inject memory
into working context.

SCOPE (PHASE 1)
---------------
The Memory Controller is limited to:
- Deterministic retrieval of candidates from:
  - Episodic memory (highest priority)
  - Facts store (immutable facts)
  - Procedural reference material (documents / SOPs / specs) as retrieval targets
- Deterministic scoring and ranking of candidates
- Deterministic assembly of a context package under a token budget
- Emission of an auditable assembly record (inputs, decisions, outputs)

The Memory Controller explicitly excludes:
- Model calls for reasoning
- Autonomous planning or execution
- Tool invocation
- Any mutation of stored memory
- Any learning or reinforcement behavior
- Any semantic promotion or summarization
- Any Forever Memory implementation (stub contract only)

PRIORITY RULES
--------------
1) Episodic memory has highest priority for recall.
2) Facts are immutable and must be presented as facts, not interpretations.
3) Meaning may evolve, but meaning is NOT produced by the Memory Controller in
   Phase 1. Phase 1 recall is selection + assembly only.

DETERMINISTIC INPUTS
--------------------
All Memory Controller outputs MUST be fully determined by:
- The query input
- The current immutable stores (as-of retrieval time)
- The configured scoring and assembly rules
- The explicit token budget

No hidden state, randomness, or undocumented heuristics are permitted.

RETRIEVAL CONTRACT
------------------
The Memory Controller MUST:
- Accept a query input (opaque payload is acceptable in Phase 1)
- Retrieve candidates from approved stores using deterministic methods
- Record retrieval parameters and store versions/identifiers in the audit record

The Memory Controller MUST NOT:
- Retrieve from unapproved sources
- Retrieve via undocumented transformations
- Retrieve via model-based interpretation in Phase 1

SCORING CONTRACT
----------------
The Memory Controller MUST:
- Apply a deterministic scoring method to candidates
- Produce a ranked list with explicit scores
- Record the scoring method and parameters in the audit record

The scoring method may be simplistic in Phase 1, but must be explicit and stable.

ASSEMBLY CONTRACT
-----------------
The Memory Controller MUST:
- Assemble a context package that fits within the provided token budget
- Prefer higher-priority sources when budgets are tight
- Preserve provenance for every included item
- Emit an assembly record containing:
  - Query input reference
  - Candidate set (identifiers only)
  - Scores and ranking
  - Selected items
  - Excluded items and reasons (budget, low score, policy)
  - Final context package manifest (ordered list)

The Memory Controller MUST NOT:
- Modify the content of recalled items
- Summarize or compress content via interpretation
- Omit provenance references for included items

FOREVER MEMORY (PHASE 1 STUB ONLY)
----------------------------------
Phase 1 defines only a stub contract:
- The system may accept the concept that storage is effectively infinite
- The Memory Controller must still be selective at recall time
- No always-on capture or “total recall” behavior is implemented in Phase 1

Any Forever Memory implementation is explicitly out of scope.

ERROR HANDLING
--------------
If retrieval or assembly fails, the Memory Controller MUST:
- Emit an auditable failure record
- Preserve enough detail to reproduce the failure deterministically
- Avoid partial or silent outputs

COMPLIANCE REFERENCES
---------------------
This contract enforces:
- CMP-001: Determinism Requirements
- CMP-003: Provenance Guarantees
- CMP-004: Autonomy Boundaries
- CMP-005: Token Limits

EXIT CONDITIONS
---------------
This contract is considered satisfied when Phase 1 processes can demonstrate:
- Deterministic retrieval/scoring/assembly under audit
- Token-budget bounded context packages
- Episodic-first prioritization
- Provenance-complete assembly records

