"""
Read-only repo tools (Phase 0)

These tools are intentionally conservative:
- no writes
- size caps
- no binary decoding assumptions beyond utf-8 with replacement
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List


_MAX_READ_BYTES = 200_000  # 200KB hard cap for Phase 0


def _safe_root(root: str) -> Path:
    p = Path(root).resolve()
    if not p.exists() or not p.is_dir():
        raise FileNotFoundError(f"root not found or not a directory: {root}")
    return p


def _safe_path_under(root: Path, rel_path: str) -> Path:
    rp = (root / rel_path).resolve()
    if root not in rp.parents and rp != root:
        raise ValueError("path escapes root")
    return rp


def repo_list_files(tool_input: Dict[str, Any]) -> Dict[str, Any]:
    """List files under a repo root (relative paths)."""
    root = str(tool_input.get("root", "."))
    max_files = int(tool_input.get("max_files", 500))

    r = _safe_root(root)
    files: List[str] = []
    for p in r.rglob("*"):
        if p.is_file():
            files.append(str(p.relative_to(r)))
            if len(files) >= max_files:
                break

    return {"root": str(r), "count": len(files), "files": sorted(files)}


def repo_read_text(tool_input: Dict[str, Any]) -> Dict[str, Any]:
    """Read a UTF-8 text file under repo root (size-capped)."""
    root = str(tool_input.get("root", "."))
    path = tool_input.get("path")
    if not isinstance(path, str) or not path.strip():
        raise ValueError("tool_input.path must be a non-empty string")

    r = _safe_root(root)
    fp = _safe_path_under(r, path)

    if not fp.exists() or not fp.is_file():
        raise FileNotFoundError(f"file not found: {path}")

    size = fp.stat().st_size
    if size > _MAX_READ_BYTES:
        raise ValueError(f"file too large for Phase 0 read_text cap: {size} bytes")

    data = fp.read_bytes()
    text = data.decode("utf-8", errors="replace")
    return {"root": str(r), "path": str(fp.relative_to(r)), "bytes": size, "text": text}
