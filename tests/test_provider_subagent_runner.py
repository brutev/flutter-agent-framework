from pathlib import Path

from flutter_agent.agents.orchestrator import SubagentSpec
from flutter_agent.agents.provider_runner import ProviderSubagentRunner
from flutter_agent.providers.base import ModelResponse
from flutter_agent.security.scope import ProjectScope
from flutter_agent.tools.registry import ToolRegistry


class FakeProvider:
    name = "fake"

    def complete(self, messages, tools):
        assert tools
        assert "analyst" in messages[-1]["content"]
        return ModelResponse("Analysis complete")


def test_provider_runner_executes_subagent_with_granted_tools(tmp_path: Path) -> None:
    runner = ProviderSubagentRunner(FakeProvider(), ToolRegistry(ProjectScope(tmp_path)))
    output = runner.run(
        SubagentSpec("analyst", "Inspect the project", frozenset({"read_file"})),
        "Feature request",
    )
    assert output == "Analysis complete"


def test_provider_runner_uses_role_specific_provider(tmp_path: Path) -> None:
    default = FakeProvider()

    class ReviewerProvider(FakeProvider):
        def complete(self, messages, tools):
            assert "reviewer" in messages[-1]["content"]
            return ModelResponse("Independent review")

    runner = ProviderSubagentRunner(
        default,
        ToolRegistry(ProjectScope(tmp_path)),
        role_providers={"reviewer": ReviewerProvider()},
    )
    output = runner.run(SubagentSpec("reviewer", "Review diff", frozenset({"read_file"})), "requirements")
    assert output == "Independent review"

