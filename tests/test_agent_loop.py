import json
from typing import Any

from flutter_agent.agent.loop import AgentLoop
from flutter_agent.contracts.model import TaskContract
from flutter_agent.costs.ledger import CostLedger
from flutter_agent.providers.base import ModelResponse, ToolCall
from flutter_agent.security.scope import ProjectScope
from flutter_agent.tools.registry import ToolRegistry


class FakeProvider:
    name = "fake"

    def __init__(self, responses: list[ModelResponse]):
        self.responses = responses
        self.requests: list[tuple[list[dict[str, Any]], list[dict[str, Any]]]] = []

    def complete(self, messages, tools):
        self.requests.append((messages, tools))
        return self.responses.pop(0)


def test_loop_executes_tool_and_returns_final_response(tmp_path):
    provider = FakeProvider([
        ModelResponse(None, (ToolCall("call-1", "write_file", {"path": "lib/a.dart", "content": "void main() {}"}),)),
        ModelResponse("Implemented the file."),
    ])
    loop = AgentLoop(provider, ToolRegistry(ProjectScope(tmp_path)), max_steps=3)

    result = loop.run("Create lib/a.dart")

    assert result.completed
    assert result.text == "Implemented the file."
    assert (tmp_path / "lib/a.dart").exists()
    assert len(provider.requests) == 2
    tool_message = provider.requests[1][0][-1]
    assert tool_message["role"] == "tool"
    assert json.loads(tool_message["content"])["ok"] is True
    assert "stay within its scope" in provider.requests[0][0][0]["content"]


def test_loop_stops_at_max_steps(tmp_path):
    provider = FakeProvider([ModelResponse(None, (ToolCall("c", "list_files", {}),))] * 3)
    loop = AgentLoop(provider, ToolRegistry(ProjectScope(tmp_path)), max_steps=2)

    result = loop.run("Keep working")

    assert not result.completed
    assert "maximum" in (result.error or "").lower()
    assert len(provider.requests) == 2


def test_loop_returns_tool_errors_to_model(tmp_path):
    provider = FakeProvider([
        ModelResponse(None, (ToolCall("c", "verify", {"command": "rm -rf ."}),)),
        ModelResponse("I could not run that command."),
    ])
    result = AgentLoop(provider, ToolRegistry(ProjectScope(tmp_path))).run("Run cleanup")

    assert result.completed
    assert "could not" in result.text
    tool_message = provider.requests[1][0][-1]
    assert json.loads(tool_message["content"])["ok"] is False


def test_loop_rejects_duplicate_tool_call_ids(tmp_path):
    provider = FakeProvider([
        ModelResponse(None, (
            ToolCall("duplicate", "list_files", {}),
            ToolCall("duplicate", "list_files", {}),
        )),
    ])
    result = AgentLoop(provider, ToolRegistry(ProjectScope(tmp_path))).run("Inspect")
    assert not result.completed
    assert "duplicate" in (result.error or "").lower()


def test_loop_rejects_false_completion_when_contract_fails(tmp_path):
    provider = FakeProvider([ModelResponse("Done")])
    loop = AgentLoop(
        provider,
        ToolRegistry(ProjectScope(tmp_path)),
        contract=TaskContract(required_files=("lib/required.dart",)),
    )
    result = loop.run("Create the required file")
    assert not result.completed
    assert "contract failed" in (result.error or "").lower()


def test_loop_stops_before_call_after_budget_is_exceeded(tmp_path):
    provider = FakeProvider([
        ModelResponse(None, (ToolCall("c", "list_files", {}),), input_tokens=1_000_000, output_tokens=0),
        ModelResponse("should not be called"),
    ])
    ledger = CostLedger(budget_usd=0.1, input_per_million=1.0, output_per_million=1.0)
    result = AgentLoop(provider, ToolRegistry(ProjectScope(tmp_path)), ledger=ledger).run("List files")
    assert not result.completed
    assert "budget" in (result.error or "").lower()
    assert len(provider.requests) == 1


def test_loop_reserves_budget_before_first_provider_call(tmp_path):
    provider = FakeProvider([ModelResponse("must not be called")])
    ledger = CostLedger(budget_usd=0.001, input_per_million=1.0, output_per_million=1.0)
    result = AgentLoop(
        provider,
        ToolRegistry(ProjectScope(tmp_path)),
        ledger=ledger,
        reserve_output_tokens=10_000,
    ).run("Expensive request")
    assert not result.completed
    assert "budget" in (result.error or "").lower()
    assert not provider.requests


def test_loop_can_finalize_after_tool_step_limit(tmp_path):
    provider = FakeProvider([
        ModelResponse(None, (ToolCall("c", "list_files", {}),)),
        ModelResponse(None, (ToolCall("c2", "list_files", {}),)),
        ModelResponse("Final summary"),
    ])
    result = AgentLoop(
        provider,
        ToolRegistry(ProjectScope(tmp_path)),
        max_steps=2,
        finalize_on_limit=True,
    ).run("Summarize")
    assert result.completed
    assert result.text == "Final summary"

