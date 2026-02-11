"""adam_os.memory.canonical

Deterministic JSON canonicalization + SHA-256 helpers used by Phase 5 memory stores.

Rules:
- JSON serialization is canonical: sorted keys, compact separators, UTF-8, no NaN/Infinity.
- Hashing is SHA-256 over UTF-8 bytes of canonical JSON strings.
- Errors are strict and deterministic.
"""

from __future__ import annotations

import hashlib
import json
from typing import Any, Dict


class CanonicalizationError(ValueError):
    """Raised when an object cannot be canonicalized deterministically."""


def canonical_dumps(obj: Any) -> str:
    """Return a canonical JSON string for obj.

    Canonical form:
    - sort_keys=True
    - separators=(',', ':') (no extra whitespace)
    - ensure_ascii=False (preserve unicode)
    - allow_nan=False (reject NaN/Infinity deterministically)
    """
    try:
        return json.dumps(
            obj,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
            allow_nan=False,
        )
    except (TypeError, ValueError) as e:
        # Deterministic error type + message prefix.
        raise CanonicalizationError(f"canonical_dumps: non-serializable input: {e}") from None


def sha256_hex(text: str) -> str:
    """Return SHA-256 hex digest of UTF-8 encoded text."""
    if not isinstance(text, str):
        raise TypeError("sha256_hex: text must be str")
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def hash_record_fields(record_dict_without_hash: Dict[str, Any]) -> str:
    """Compute a deterministic hash for a record dict (excluding any existing 'hash' field).

    - Requires a dict input
    - Refuses a dict containing 'hash' to avoid accidental double-hashing
    """
    if not isinstance(record_dict_without_hash, dict):
        raise TypeError("hash_record_fields: record_dict_without_hash must be dict")
    if "hash" in record_dict_without_hash:
        raise ValueError("hash_record_fields: input must not contain 'hash' field")
    canon = canonical_dumps(record_dict_without_hash)
    return sha256_hex(canon)


__all__ = [
    "CanonicalizationError",
    "canonical_dumps",
    "sha256_hex",
    "hash_record_fields",
]
