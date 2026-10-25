from dataclasses import dataclass

from flutter_agent.tasks.models import TaskType
from flutter_agent.verification.models import CheckSpec


@dataclass(frozen=True)
class PlaybookStage:
    name: str
    objective: str
    allowed_tools: frozenset[str]


@dataclass(frozen=True)
class Playbook:
    name: str
    use_when: str
    task_types: tuple[TaskType, ...]
    required_inputs: tuple[str, ...]
    stages: tuple[PlaybookStage, ...]
    acceptance_criteria: tuple[str, ...]
    verification_checks: tuple[CheckSpec, ...]
    failure_recovery: str
    artifacts: tuple[str, ...]

    def __post_init__(self) -> None:
        if not self.name or not self.stages:
            raise ValueError("Playbooks require a name and at least one stage")
        names = tuple(stage.name for stage in self.stages)
        if len(names) != len(set(names)):
            raise ValueError(f"Playbook contains duplicate stages: {self.name}")
