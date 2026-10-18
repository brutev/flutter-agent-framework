from flutter_agent.agent.loop import AgentLoop
from flutter_agent.costs.ledger import CostLedger
from flutter_agent.agents.orchestrator import SubagentSpec, SubagentRunner
from flutter_agent.agents.permissions import RestrictedTools
from flutter_agent.providers.base import ModelProvider
from flutter_agent.tools.registry import ToolRegistry


class ProviderSubagentRunner(SubagentRunner):
    """Runs one bounded provider-backed subagent with restricted tools."""

    def __init__(self, provider: ModelProvider, registry: ToolRegistry, max_steps: int = 6, ledger: CostLedger | None = None):
        self.provider = provider
        self.registry = registry
        self.max_steps = max_steps
        self.ledger = ledger

    def run(self, spec: SubagentSpec, context: str) -> str:
        restricted = RestrictedTools(self.registry, spec.allowed_tools)
        task = (
            f"You are the {spec.role} subagent.\n"
            f"Role instructions: {spec.prompt}\n"
            f"Shared context:\n{context}"
        )
        result = AgentLoop(self.provider, restricted, max_steps=self.max_steps, ledger=self.ledger, finalize_on_limit=True).run(task)
        if not result.completed:
            raise RuntimeError(result.error or f"Subagent {spec.role} did not complete")
        return result.text or ""

