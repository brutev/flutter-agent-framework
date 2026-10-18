import os
import re


def redact_secrets(text: str, secrets: list[str] | None = None) -> str:
    """Remove known key values and common bearer/API-key patterns from logs."""
    values = [value for value in (secrets or []) if value]
    result = text
    for value in values:
        result = result.replace(value, "[REDACTED]")
    result = re.sub(r'(?i)(bearer\s+|api[_-]?key[=:]\s*)[^\s,;"}]+', r"\1[REDACTED]", result)
    return result
