from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path


CURRENT_STATE_VERSION = 1


class StateMigrationError(RuntimeError):
    pass


@dataclass(frozen=True)
class StateManifest:
    version: int
    migrated_at: str


def ensure_state(project_root: Path) -> StateManifest:
    """Create or migrate the project-local framework state manifest."""
    directory = project_root / ".flutter-agent"
    directory.mkdir(parents=True, exist_ok=True)
    path = directory / "state.json"
    if not path.exists():
        manifest = StateManifest(CURRENT_STATE_VERSION, datetime.now(timezone.utc).isoformat())
        path.write_text(json.dumps(manifest.__dict__, indent=2) + "\n", encoding="utf-8")
        return manifest
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        version = int(data.get("version", 0))
    except (OSError, ValueError, TypeError, json.JSONDecodeError) as exc:
        raise StateMigrationError(f"Invalid framework state manifest: {path}") from exc
    if version > CURRENT_STATE_VERSION:
        raise StateMigrationError(
            f"State version {version} is newer than this framework supports ({CURRENT_STATE_VERSION})"
        )
    if version < CURRENT_STATE_VERSION:
        # Version 1 only introduces the manifest; future versions should add
        # explicit transformations here instead of silently rewriting state.
        data["version"] = CURRENT_STATE_VERSION
        data["migrated_at"] = datetime.now(timezone.utc).isoformat()
        path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
    return StateManifest(int(data["version"]), str(data.get("migrated_at", "")))
