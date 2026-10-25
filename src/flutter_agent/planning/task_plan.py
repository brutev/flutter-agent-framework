from dataclasses import dataclass

from flutter_agent.skills.catalog import Skill
from flutter_agent.contracts.model import TaskContract
from flutter_agent.playbooks.models import Playbook


@dataclass(frozen=True)
class PlanStage:
    role: str
    prompt: str
    allowed_tools: frozenset[str]


@dataclass(frozen=True)
class TaskPlan:
    task: str
    stages: tuple[PlanStage, ...]
    selected_skills: tuple[str, ...]
    playbook: str = "legacy_feature"
    rationale: str = "Default controlled development workflow"


def build_plan(
    task: str,
    skills: list[Skill] | tuple[Skill, ...],
    contract: TaskContract | None = None,
    playbook: Playbook | None = None,
    rationale: str = "Default controlled development workflow",
) -> TaskPlan:
    if not task.strip():
        raise ValueError("Task must not be empty")
    selected = tuple(skill.name for skill in skills)
    skill_context = ", ".join(selected) if selected else "general Flutter development"
    skill_instructions = "\n".join(skill.instructions for skill in skills if skill.instructions)
    guidance = f"\nSkill guidance:\n{skill_instructions}" if skill_instructions else ""
    contract_context = ""
    if contract is not None:
        contract_context = (
            f"\nContract required files: {', '.join(contract.required_files) or 'none'}"
            f"\nContract required symbols: {', '.join(contract.required_symbols) or 'none'}"
            f"\nContract forbidden content: {', '.join(contract.forbidden_content) or 'none'}"
        )
    read = frozenset({"list_files", "read_file", "search_code"})
    verify = read | frozenset({"verify"})
    write = read | frozenset({"write_file"})
    if playbook is None:
        stages = (
            PlanStage("analyst", f"Inspect only the evidence needed, then return a concise architecture summary. Stop after a few read-only tool calls; do not keep exploring. Skills: {skill_context}{guidance}", read),
            PlanStage("implementer", f"Implement the requested task using the analysis and skills: {skill_context}{guidance}{contract_context}. After editing, return a concise completion summary.", write),
            PlanStage("tester", f"Run focused verification and inspect test coverage, then summarize the result and stop.{guidance}", verify),
            PlanStage("reviewer", f"Review the changes for standards, security, and scope violations, then return a final review summary and stop.{guidance}{contract_context}", verify),
        )
        return TaskPlan(task, stages, selected, rationale=rationale)

    stages = tuple(
        PlanStage(
            stage.name,
            f"{stage.objective}\nPlaybook: {playbook.name}. Skills: {skill_context}{guidance}{contract_context}",
            stage.allowed_tools,
        )
        for stage in playbook.stages
    )
    return TaskPlan(task, stages, selected, playbook.name, rationale)

