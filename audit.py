"""Small JSON-backed append-only audit trail."""

import json
from pathlib import Path

from models import AuditEntry


def append_audit_entry(entry: AuditEntry, path: str | Path = "audit_log.json") -> None:
    destination = Path(path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    try:
        entries = json.loads(destination.read_text(encoding="utf-8")) if destination.exists() else []
        if not isinstance(entries, list):
            raise ValueError("audit log must contain a JSON list")
    except (json.JSONDecodeError, UnicodeDecodeError) as exc:
        raise ValueError(f"Cannot read audit log {destination}: {exc}") from exc
    entries.append(entry.model_dump())
    destination.write_text(json.dumps(entries, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def load_audit_entries(path: str | Path = "audit_log.json") -> list[AuditEntry]:
    destination = Path(path)
    if not destination.exists():
        return []
    raw = json.loads(destination.read_text(encoding="utf-8"))
    return [AuditEntry.model_validate(item) for item in raw]

