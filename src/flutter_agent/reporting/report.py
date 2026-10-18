from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Any


@dataclass(frozen=True)
class DeliveryReport:
    task: str
    completed: bool
    stages: tuple[str, ...] = ()
    outputs: tuple[str, ...] = ()
    error: str | None = None
    findings: tuple[str, ...] = ()
    generated_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["stages"] = list(self.stages)
        data["outputs"] = list(self.outputs)
        data["findings"] = list(self.findings)
        return data

