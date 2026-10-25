from flutter_agent.agent.loop import AgentLoop
from flutter_agent.costs.ledger import CostLedger
from flutter_agent.agents.orchestrator import SubagentSpec, SubagentRunner
from flutter_agent.agents.permissions import RestrictedTools
from flutter_agent.providers.base import ModelProvider
from flutter_agent.tools.registry import ToolRegistry


class ProviderSubagentRunner(SubagentRunner):
    """Runs one bounded provider-backed subagent with restricted tools."""

    def __init__(self, provider: ModelProvider, registry: ToolRegistry, max_steps: int = 6, ledger: CostLedger | None = None, reserve_output_tokens: int = 4096, role_providers: dict[str, ModelProvider] | None = None):
        self.provider = provider
        self.registry = registry
        self.max_steps = max_steps
        self.ledger = ledger
        self.reserve_output_tokens = reserve_output_tokens
        self.role_providers = role_providers or {}

    def run(self, spec: SubagentSpec, context: str) -> str:
        restricted = RestrictedTools(self.registry, spec.allowed_tools)
        task = (
            f"You are the {spec.role} subagent.\n"
            f"Role instructions: {spec.prompt}\n"
            f"Shared context:\n{context}"
        )
        provider = self.role_providers.get(spec.role, self.provider)
        result = AgentLoop(provider, restricted, max_steps=self.max_steps, ledger=self.ledger, finalize_on_limit=True, reserve_output_tokens=self.reserve_output_tokens).run(task)
        if not result.completed:
            raise RuntimeError(result.error or f"Subagent {spec.role} did not complete")
        return result.text or ""

