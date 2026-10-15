"""Append-only audit trail: every agent-loop step goes into output/audit_trail.json."""

import json
import os
import threading
from datetime import datetime
from pathlib import Path
from typing import Any

from models import AuditRecord

AUDIT_PATH = Path(__file__).resolve().parent.parent / "output" / "audit_trail.json"
MAX_FIELD_CHARS = 2000  # keep the file readable; long tool results are truncated

_lock = threading.Lock()


def _clip(value: Any) -> Any:
    if isinstance(value, str):
        return value if len(value) <= MAX_FIELD_CHARS else value[:MAX_FIELD_CHARS] + f"... [+{len(value) - MAX_FIELD_CHARS} chars]"
    if isinstance(value, dict):
        return {k: _clip(v) for k, v in value.items()}
    if isinstance(value, list):
        return [_clip(v) for v in value]
    return value


def _load() -> list[dict]:
    if not AUDIT_PATH.exists():
        return []
    try:
        data = json.loads(AUDIT_PATH.read_text() or "[]")
    except json.JSONDecodeError:
        # Never lose old records: keep the unreadable file aside and start a new list.
        AUDIT_PATH.rename(AUDIT_PATH.with_suffix(f".corrupt-{datetime.now():%Y%m%d%H%M%S}.json"))
        return []
    return data if isinstance(data, list) else [data]


def append(record: AuditRecord) -> None:
    """Add one record to the end of the trail. Existing records are never rewritten or dropped."""
    entry = _clip(record.model_dump(mode="json"))
    with _lock:
        AUDIT_PATH.parent.mkdir(parents=True, exist_ok=True)
        records = _load()
        records.append(entry)
        tmp = AUDIT_PATH.with_suffix(".json.tmp")
        tmp.write_text(json.dumps(records, indent=2, default=str))
        os.replace(tmp, AUDIT_PATH)


def read_all() -> list[dict]:
    """Every record so far, oldest first."""
    with _lock:
        return _load()


def append_human(action: str, who: str, result: dict) -> None:
    """Record a human approval/rejection made on the dashboard."""
    append(AuditRecord(
        timestamp=now(), run_id="human", ticket_id=(result.get("approval") or result).get("ticket_id"),
        agent="human", depth=0, chain=[], step=0, event="human_decision",
        detail={"action": action, "by": who, "result": result},
    ))


def append_reset(who: str = "dashboard") -> None:
    """Mark a database reset, so earlier runs no longer count as the tickets' current state."""
    append(AuditRecord(
        timestamp=now(), run_id="reset", ticket_id=None, agent="human", depth=0, chain=[], step=0,
        event="reset", detail={"action": "reset working database", "by": who},
    ))


def now() -> str:
    return datetime.now().astimezone().isoformat(timespec="seconds")
