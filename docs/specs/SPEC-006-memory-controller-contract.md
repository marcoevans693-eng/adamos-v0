================================================================================
SPEC-006 — Memory Controller Contract
Doc-ID: SPEC-006
Project: AdamOS v0
Status: Draft
================================================================================

PURPOSE
-------
Define the Phase 6 contract for deterministic memory retrieval, scoring, and
bounded context assembly.

This spec governs:
- deterministic JSONL store reading (candidate extraction)
- deterministic scoring + ordering
- strict token-budgeted context package assembly
- constraints on ledger receipts (metadata-only)

SCOPE
-----
IN SCOPE (Phase 6):
- Read-only retrieval from explicit memory stores (JSONL)
- Deterministic scoring and ordering of candidates
- Bounded selection and truncation under an explicit token budget
- ContextPackage output schema (stable + hashable)
- memory.read tool contract (read-only)
- Success-only receipt metadata (no raw memory content)

OUT OF SCOPE (NON-GOALS):
- semantic promotion / embedding / vector search / reranking
- autonomous behavior or agent loops
- probabilistic scoring (LLM-based scoring, embeddings, classifiers)
- store mutation, store compaction, or rewriting JSONL
- “Forever Memory” or multi-store semantic layers
- writing raw memory excerpts into the run ledger
- trust becoming anything other than detection-only filtering

TERMS
-----
Memory Store:
- A read-only append-only JSONL file containing memory records.

Candidate:
- A normalized in-memory object extracted from a memory record and eligible for scoring.

Context Package (ContextPackage):
- The deterministic, bounded output representing selected memory excerpts plus budget metadata.

Token Budget:
- A declared upper bound on excerpt tokens used in ContextPackage assembly.

Trust (Phase 4 contract):
- Detection-only classification events; Memory Controller may filter only items explicitly
  classified malicious (or equivalent explicit deny classification), and MUST NOT “infer”
  trust.

INPUT CONTRACT
--------------
MemoryControllerInput (logical input):
- query: string (required, non-empty after trim)
- store_paths: list[string] (required, non-empty; explicit absolute or repo-relative paths)
- budget:
    - max_excerpt_tokens: int (required, > 0)
    - per_item_max_excerpt_tokens: int (optional, defaults to max_excerpt_tokens)
    - max_items: int (optional, defaults to 50; hard cap)
- scoring:
    - enable_recency_weight: bool (optional, default false)
    - recency_half_life_days: int (optional, default 30; only used if enable_recency_weight=true)
    - enable_tag_overlap: bool (optional, default true)
    - query_terms: list[string] (optional; if absent, derived deterministically from query)
- trust_filter:
    - deny_classifications: list[string] (optional default ["malicious"])
    - trust_snapshot_path: string (optional; if provided, used read-only to filter)
- now_utc:
    - string (optional ISO8601 UTC timestamp). If absent, recency weighting MUST be disabled.

Determinism Rules (Inputs):
- The controller MUST treat missing optional fields as the defaults above.
- The controller MUST NOT consult system time unless now_utc is explicitly provided.
- The controller MUST NOT consult network, environment randomness, or non-deterministic sources.

OUTPUT CONTRACT
---------------
ContextPackage (JSON-serializable object):
{
  "query": {
    "raw": string,
    "query_hash": string
  },
  "budget": {
    "max_excerpt_tokens": int,
    "used_excerpt_tokens": int,
    "remaining_excerpt_tokens": int,
    "per_item_max_excerpt_tokens": int,
    "max_items": int
  },
  "selection": {
    "selected": [
      {
        "memory_id": string,
        "record_hash": string,
        "store_path": string,
        "score": number,
        "excerpt": string,
        "excerpt_tokens": int
      }
    ],
    "dropped": [
      {
        "memory_id": string,
        "record_hash": string,
        "store_path": string,
        "reason": string
      }
    ]
  },
  "package_hash": string,
  "controller_version": "phase6-v1"
}

Contract Notes:
- excerpt MUST be truncated deterministically (see TRUNCATION).
- record_hash MUST be stable across runs for identical record content (see HASHING).
- package_hash MUST be stable across runs for identical inputs and identical store contents.

JSONL STORE RECORD CONTRACT (MINIMUM)
-------------------------------------
A JSONL line is one JSON object (UTF-8). Minimum accepted fields:
- memory_id: string (required)
- ts_utc: string (optional ISO8601 UTC timestamp)
- text: string (required; may be empty but discouraged)
- tags: list[string] (optional)
- refs: list[object] (optional; if present MUST be list[dict])

If a record fails schema validation, it MUST be ignored and counted as dropped with reason:
"invalid_record_schema".

READER CONTRACT
---------------
Reader Behavior:
- Input: store_paths list
- Output: candidates in deterministic order
- Read strategy: streaming line-by-line, no buffering dependent on OS non-determinism
- Deterministic iteration order:
    1) store_paths MUST be normalized and sorted lexicographically before read
    2) within each store, read in file order (line order)
- Candidate normalization must produce:
    - memory_id (string)
    - store_path (string)
    - ts_utc (optional normalized timestamp string)
    - text (string)
    - tags (sorted unique list[string], lowercased)
    - refs (validated list[dict] or empty list)
    - record_hash (stable; see HASHING)

HASHING
-------
record_hash:
- MUST be computed from a canonical JSON serialization of the normalized record:
  keys sorted, UTF-8, no whitespace variance.
- Recommended: SHA-256 hex of canonical bytes.

query_hash:
- MUST be SHA-256 hex of the normalized query:
  trim, collapse internal whitespace to single spaces, lowercased.

package_hash:
- MUST be SHA-256 hex of a canonical JSON serialization of the ContextPackage
  excluding only fields that would vary without store changes.
- package_hash MUST include selected items (memory_id, record_hash, store_path,
  score, excerpt_tokens) and MUST include budget fields.

TOKEN BUDGETING (DETERMINISTIC ESTIMATOR)
-----------------------------------------
Phase 6 uses a deterministic estimator (not model-exact).

Estimator:
- excerpt_tokens = ceil(utf8_byte_length(excerpt) / 4)

Rules:
- used_excerpt_tokens = sum(excerpt_tokens for selected)
- remaining_excerpt_tokens = max_excerpt_tokens - used_excerpt_tokens (floor at 0)
- Selection MUST stop when:
    - used_excerpt_tokens would exceed max_excerpt_tokens, OR
    - selected count reaches max_items

SCORING (DETERMINISTIC)
-----------------------
The scorer MUST be pure deterministic math.

Query term derivation (if scoring.query_terms absent):
1) normalize query: trim, lower, collapse whitespace
2) split on whitespace
3) drop empty terms
4) keep terms length >= 2
5) stable order: preserve original appearance order, then unique (first occurrence wins)

Base relevance score:
- term_match_count = number of query_terms that appear as substrings in normalized candidate text
- base = term_match_count

Tag overlap bonus (optional, enable_tag_overlap=true):
- overlap = count of query_terms that exactly match any candidate tag
- tag_bonus = overlap * 0.5

Recency weight (optional, enable_recency_weight=true):
- Only allowed if now_utc is provided and candidate ts_utc is valid.
- age_days = (now_utc - ts_utc) in days (deterministic parse; invalid => no recency)
- weight = 0.5 ** (age_days / recency_half_life_days)
- recency_bonus = weight (bounded [0,1])

Final score:
- score = base + tag_bonus + recency_bonus

Tie-breaking (STABLE):
Candidates MUST be ordered by:
1) score descending
2) ts_utc descending (missing ts_utc sorts last)
3) store_path ascending
4) memory_id ascending
5) record_hash ascending

TRUST FILTERING (DETECTION-ONLY)
-------------------------------
Filtering is allowed ONLY if:
- a trust snapshot exists AND explicitly marks a memory_id (or record_hash) with a deny classification
  in trust_filter.deny_classifications.

Rules:
- No inference, no heuristics, no “suspicious” scoring.
- If no snapshot provided, trust filtering is disabled.
- Filtered candidates MUST appear in dropped with reason "trust_denied".

TRUNCATION (DETERMINISTIC EXCERPT)
----------------------------------
Excerpt construction:
- Normalize text: preserve original text bytes as-is (no rewriting), except:
  - strip leading/trailing whitespace
- If text is empty after strip => excerpt is "" and excerpt_tokens=0

Per-item truncation:
- per_item_max_excerpt_tokens = min(per_item_max_excerpt_tokens, max_excerpt_tokens)
- Determine max_bytes = per_item_max_excerpt_tokens * 4
- excerpt = first max_bytes of UTF-8 bytes of normalized text, decoded with strict UTF-8.
  If a cut splits a codepoint, cut back to last valid boundary (deterministic).
- excerpt_tokens computed via estimator above.

Global selection under budget:
- Iterate candidates in sorted order.
- For each candidate, compute its excerpt (per-item truncation), then:
  - if used + excerpt_tokens <= max_excerpt_tokens => select
  - else => drop with reason "budget_exhausted"

LEDGER RECEIPT CONSTRAINTS (SUCCESS-ONLY, METADATA-ONLY)
--------------------------------------------------------
The dispatcher receipt for memory.read success MUST include ONLY:
- kind = "memory.read"
- data:
    - query_hash
    - store_paths (as provided or normalized; must be deterministic)
    - selected_count
    - package_hash

The receipt MUST NOT include:
- excerpts
- raw memory text
- tags, refs, or any payload that reconstructs memory content

ERROR HANDLING
--------------
memory.read MUST fail fast with structured errors if:
- query missing/empty
- store_paths missing/empty
- budget.max_excerpt_tokens <= 0
- store_paths contains a path that does not exist (policy choice):
  - Phase 6 default: treat missing store as error (fail), not partial success

Determinism requirement:
- The same invalid inputs MUST produce the same error type and message.

COMPATIBILITY + VERSIONING
--------------------------
- controller_version MUST be "phase6-v1" until Phase 6 closes.
- Any future changes require a new spec and explicit version bump.

SECURITY + PRIVACY
------------------
- Controller is read-only.
- No network access.
- No tool invocation besides reading stores.
- No raw memory content enters the run ledger.

ACCEPTANCE CRITERIA (PHASE 6)
-----------------------------
A Phase 6 implementation is compliant if:
- Given identical inputs and identical store contents, ContextPackage (including package_hash)
  is identical across runs.
- Ledger receipt is metadata-only and success-only.
- No store mutation occurs.
- Trust filtering is detection-only and explicitly deny-listed.
