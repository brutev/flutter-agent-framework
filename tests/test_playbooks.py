from flutter_agent.contracts.model import TaskContract
from flutter_agent.planning.task_plan import build_plan
from flutter_agent.playbooks import PlaybookRegistry
from flutter_agent.routing.router import route_task


def test_builtin_playbooks_have_complete_contracts() -> None:
    registry = PlaybookRegistry()
    expected = {
        "investigate",
        "bug_fix",
        "feature",
        "refactor",
        "code_review",
        "flutter_quality",
        "release_readiness",
    }
    assert {playbook.name for playbook in registry.all()} == expected
    for playbook in registry.all():
        assert playbook.use_when
        assert playbook.required_inputs
        assert playbook.stages
        assert playbook.acceptance_criteria
        assert playbook.failure_recovery
        assert playbook.artifacts


def test_router_selects_inspectable_playbook_and_rationale() -> None:
    decision = route_task("Refactor the login repository without behavior changes")
    assert decision.playbook == "refactor"
    assert decision.rationale
    assert "verification report" in decision.evidence_required


def test_plan_uses_selected_playbook_permissions() -> None:
    playbook = PlaybookRegistry().get("investigate")
    plan = build_plan(
        "Inspect navigation",
        [],
        TaskContract(),
        playbook,
        "Read-only request",
    )
    assert plan.playbook == "investigate"
    assert [stage.role for stage in plan.stages] == ["analyst", "reviewer"]
    assert all("write_file" not in stage.allowed_tools for stage in plan.stages)
