from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Any

from flutter_agent.tasks.models import TaskRecord


@dataclass(frozen=True)
class DeliveryReport:
    task: str
    completed: bool
    stages: tuple[str, ...] = ()
    outputs: tuple[str, ...] = ()
    error: str | None = None
    findings: tuple[str, ...] = ()
    status: str | None = None
    verification: dict[str, Any] | None = None
    task_record: dict[str, Any] | None = None
    generated_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["stages"] = list(self.stages)
        data["outputs"] = list(self.outputs)
        data["findings"] = list(self.findings)
        data["status"] = self.status or ("VERIFIED" if self.completed else "FAILED")
        return data

    @classmethod
    def from_task(
        cls,
        task: TaskRecord,
        *,
        completed: bool,
        stages: tuple[str, ...] = (),
        outputs: tuple[str, ...] = (),
        error: str | None = None,
        findings: tuple[str, ...] = (),
        verification: dict[str, Any] | None = None,
    ) -> "DeliveryReport":
        return cls(
            task=task.user_goal,
            completed=completed,
            stages=stages,
            outputs=outputs,
            error=error,
            findings=findings,
            status=task.status.value,
            verification=verification,
            task_record=task.to_dict(),
        )

