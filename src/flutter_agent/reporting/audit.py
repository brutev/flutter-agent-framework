import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from flutter_agent.security.secrets import redact_secrets


class AuditLog:
    """Append-only, redacted JSONL audit trail for agent runs."""

    def __init__(self, project_root: Path):
        directory = project_root / ".flutter-agent" / "audit"
        directory.mkdir(parents=True, exist_ok=True)
        self.path = directory / "events.jsonl"

    def record(self, event: str, **fields: Any) -> None:
        payload = {"timestamp": datetime.now(timezone.utc).isoformat(), "event": event}
        payload.update(fields)
        line = redact_secrets(json.dumps(payload, default=str))
        with self.path.open("a", encoding="utf-8") as handle:
            handle.write(line + "\n")
