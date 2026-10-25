import json
from dataclasses import dataclass
from typing import Any

from flutter_agent.contracts.model import TaskContract
from flutter_agent.contracts.validator import validate_contract
from flutter_agent.costs.ledger import CostLedger
from flutter_agent.providers.base import ModelProvider
from flutter_agent.tools.registry import ToolRegistry


@dataclass(frozen=True)
class AgentResult:
    completed: bool
    text: str | None = None
    error: str | None = None
    steps: int = 0


class AgentLoop:
    """Bounded model/tool loop with no direct filesystem authority."""

    def __init__(self, provider: ModelProvider, tools: ToolRegistry, max_steps: int = 12, contract: TaskContract | None = None, ledger: CostLedger | None = None, finalize_on_limit: bool = False, reserve_output_tokens: int = 4096):
        if max_steps < 1:
            raise ValueError("max_steps must be at least 1")
        self.provider = provider
        self.tools = tools
        self.max_steps = max_steps
        self.contract = contract
        self.ledger = ledger
        self.finalize_on_limit = finalize_on_limit
        self.reserve_output_tokens = reserve_output_tokens

    def _budget_allows(self, messages: list[dict[str, Any]]) -> bool:
        if self.ledger is None:
            return True
        estimated_input = max(1, len(json.dumps(messages, default=str)) // 4)
        return self.ledger.can_reserve(estimated_input, self.reserve_output_tokens)

    def run(self, task: str) -> AgentResult:
        if not task.strip():
            return AgentResult(False, error="Task must not be empty")
        scope = getattr(self.tools, "scope", None)
        if scope is None:
            restricted_registry = getattr(self.tools, "registry", None)
            scope = getattr(restricted_registry, "scope", None)
        root_text = str(scope.root) if scope is not None else "the assigned project root"
        messages: list[dict[str, Any]] = [
            {
                "role": "system",
                "content": (
                    "You are a governed Flutter development agent. Use tools only when needed. "
                    "Answer exactly the requested task and stay within its scope. Do not add unsolicited "
                    "recommendations, assumptions, or next steps unless explicitly requested. "
                    f"The active project root is {root_text}. Use only paths inside this root; "
                    "never invent paths from another operating system."
                ),
            },
            {"role": "user", "content": task},
        ]

        for step in range(1, self.max_steps + 1):
            if not self._budget_allows(messages):
                return AgentResult(False, error="Insufficient model budget for the next bounded request", steps=step - 1)
            try:
                response = self.provider.complete(messages, self.tools.schemas())
            except Exception as exc:  # provider failures become an honest run result
                return AgentResult(False, error=f"Provider failure: {exc}", steps=step)
            if self.ledger is not None:
                self.ledger.record(response.input_tokens, response.output_tokens)

            call_ids = [call.id for call in response.tool_calls]
            if any(not call_id for call_id in call_ids) or len(call_ids) != len(set(call_ids)):
                return AgentResult(False, error="Provider returned empty or duplicate tool-call IDs", steps=step)

            if not response.tool_calls:
                if self.contract is not None:
                    contract_result = validate_contract(self.tools.scope.root, self.contract)
                    if not contract_result.passed:
                        return AgentResult(
                            False,
                            text=response.text,
                            error="Contract failed: " + "; ".join(contract_result.findings),
                            steps=step,
                        )
                return AgentResult(True, text=response.text or "", steps=step)

            assistant_tool_calls = []
            for call in response.tool_calls:
                assistant_tool_calls.append(
                    {
                        "id": call.id,
                        "type": "function",
                        "function": {
                            "name": call.name,
                            "arguments": json.dumps(call.arguments),
                        },
                    }
                )
            messages.append(
                {
                    "role": "assistant",
                    "content": response.text,
                    "tool_calls": assistant_tool_calls,
                }
            )

            for call in response.tool_calls:
                result = self.tools.execute(call.name, call.arguments)
                payload = {"ok": result.ok}
                if result.ok:
                    payload["value"] = result.value
                else:
                    payload["error"] = result.error
                messages.append(
                    {
                        "role": "tool",
                        "tool_call_id": call.id,
                        "content": json.dumps(payload, default=str),
                    }
                )

        if self.finalize_on_limit:
            final_messages = messages + [{"role": "user", "content": "Stop using tools. Return a concise final summary based only on the evidence collected."}]
            if not self._budget_allows(final_messages):
                return AgentResult(False, error="Insufficient model budget for finalization", steps=self.max_steps)
            try:
                final = self.provider.complete(
                    final_messages,
                    [],
                )
                if self.ledger is not None:
                    self.ledger.record(final.input_tokens, final.output_tokens)
                if not final.tool_calls:
                    return AgentResult(True, text=final.text or "", steps=self.max_steps + 1)
            except Exception as exc:
                return AgentResult(False, error=f"Finalization failed: {exc}", steps=self.max_steps)
        return AgentResult(False, error="Reached maximum agent steps", steps=self.max_steps)

