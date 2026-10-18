from flutter_agent.planning.task_plan import build_plan
from flutter_agent.contracts.model import TaskContract
from flutter_agent.skills.catalog import Skill


def test_plan_contains_controlled_development_stages() -> None:
    plan = build_plan("Add a Cubit login feature", [Skill("cubit", "guidance", ("cubit",))])
    assert [stage.role for stage in plan.stages] == ["analyst", "implementer", "tester", "reviewer"]
    assert "cubit" in plan.selected_skills
    assert "guidance" in plan.stages[1].prompt
    assert "write_file" not in plan.stages[0].allowed_tools
    assert "write_file" in plan.stages[1].allowed_tools


def test_plan_rejects_empty_task() -> None:
    try:
        build_plan("", [])
    except ValueError as exc:
        assert "task" in str(exc).lower()
    else:
        raise AssertionError("empty task was accepted")


def test_plan_includes_contract_constraints() -> None:
    contract = TaskContract(required_files=("lib/login.dart",), required_symbols=("LoginCubit",))
    plan = build_plan("Add login", [], contract)
    assert "lib/login.dart" in plan.stages[1].prompt
    assert "LoginCubit" in plan.stages[3].prompt

