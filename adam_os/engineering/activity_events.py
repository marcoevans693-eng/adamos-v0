from __future__ import annotations

from typing import Any, Dict, Optional

from adam_os.tools.engineering_log_append import append_engineering_event


def log_tool_execution(
    *,
    created_at_utc: str,
    tool_name: str,
    status: str,
    request_id: Optional[str] = None,
    artifact_id: Optional[str] = None,
    error_id: Optional[str] = None,
    extra: Optional[Dict[str, Any]] = None,
) -> str:
    event: Dict[str, Any] = {
        "created_at_utc": created_at_utc,
        "event_type": "tool_execute",
        "tool_name": tool_name,
        "status": status,
    }

    if request_id is not None:
        event["request_id"] = request_id
    if artifact_id is not None:
        event["artifact_id"] = artifact_id
    if error_id is not None:
        event["error_id"] = error_id

    if extra:
        for k, v in extra.items():
            event[k] = v

    return append_engineering_event(event)
