from pathlib import Path

from flutter_agent.agents.orchestrator import SequentialOrchestrator, SubagentSpec
from flutter_agent.agents.provider_runner import ProviderSubagentRunner
from flutter_agent.contracts.model import TaskContract
from flutter_agent.contracts.validator import validate_contract
from flutter_agent.planning.task_plan import build_plan
from flutter_agent.project.profile import detect_profile
from flutter_agent.providers.base import ModelResponse, ToolCall
from flutter_agent.security.scope import ProjectScope
from flutter_agent.skills.catalog import SkillCatalog
from flutter_agent.tools.registry import ToolRegistry


class FixtureProvider:
    name = "fixture"

    def __init__(self):
        self.calls = 0

    def complete(self, messages, tools):
        self.calls += 1
        if self.calls == 2:
            return ModelResponse(None, (ToolCall("write", "write_file", {"path": "lib/login.dart", "content": "class LoginCubit {}"}),))
        return ModelResponse(f"stage {self.calls} complete")


def test_framework_pipeline_smoke(tmp_path: Path) -> None:
    (tmp_path / "pubspec.yaml").write_text("dependencies:\n  flutter_bloc: ^8.0.0\n", encoding="utf-8")
    (tmp_path / "lib" / "domain").mkdir(parents=True)
    (tmp_path / "lib" / "data").mkdir()
    profile = detect_profile(tmp_path)
    plan = build_plan("Add login Cubit", SkillCatalog().select("Add login Cubit"), TaskContract(("lib/login.dart",), ("LoginCubit",)))
    specs = [SubagentSpec(stage.role, stage.prompt, stage.allowed_tools) for stage in plan.stages]
    result = SequentialOrchestrator(ProviderSubagentRunner(FixtureProvider(), ToolRegistry(ProjectScope(tmp_path)))).run(specs, str(profile))
    assert result.completed
    assert validate_contract(tmp_path, TaskContract(("lib/login.dart",), ("LoginCubit",))).passed

