from pathlib import Path
import json
from datetime import datetime, timezone
from typing import Optional

try:
    import typer
except ModuleNotFoundError:  # Keep the CLI usable in an offline standard Python environment.
    import argparse
    import sys

    class _FallbackExit(Exception):
        def __init__(self, code: int = 0):
            self.code = code

    class _FallbackClickException(Exception):
        pass

    class _FallbackTyper:
        Exit = _FallbackExit
        ClickException = _FallbackClickException

        def __init__(self, **_kwargs):
            pass

        def command(self, *_args, **_kwargs):
            return lambda function: function

        @staticmethod
        def Option(default=None, *_args, **_kwargs):
            return default

        @staticmethod
        def echo(value=""):
            print(value)

    typer = _FallbackTyper()
    typer.Typer = _FallbackTyper

    def _fallback_main() -> None:
        parser = argparse.ArgumentParser(description="Governed coding agent for Flutter projects")
        commands = parser.add_subparsers(dest="command", required=True)
        doctor_parser = commands.add_parser("doctor")
        doctor_parser.add_argument("--project", type=Path, default=Path.cwd())
        run_parser = commands.add_parser("run")
        run_parser.add_argument("task")
        run_parser.add_argument("--project", type=Path, default=Path.cwd())
        run_parser.add_argument("--provider")
        run_parser.add_argument("--model")
        run_parser.add_argument("--max-steps", type=int)
        run_parser.add_argument("--budget-usd", type=float)
        run_parser.add_argument("--contract-file", type=Path)
        run_parser.add_argument("--single-agent", dest="workflow", action="store_false")
        run_parser.set_defaults(workflow=True)
        args = parser.parse_args()
        try:
            if args.command == "doctor":
                doctor(args.project)
            else:
                run(args.task, args.project, args.provider, args.model, args.max_steps, args.budget_usd, args.contract_file, args.workflow)
        except _FallbackClickException as exc:
            parser.error(str(exc))
        except _FallbackExit as exc:
            raise SystemExit(exc.code)

from flutter_agent.agent.loop import AgentLoop
from flutter_agent.agents.orchestrator import SequentialOrchestrator, SubagentSpec
from flutter_agent.agents.provider_runner import ProviderSubagentRunner
from flutter_agent.config import AgentConfig, ProviderConfig
from flutter_agent.config_loader import load_agent_config
from flutter_agent.costs.ledger import CostLedger
from flutter_agent.contracts.loader import load_contract
from flutter_agent.contracts.validator import validate_contract
from flutter_agent.providers.registry import create_provider
from flutter_agent.providers.fallback import FallbackProvider
from flutter_agent.providers.resilience import ResilientProvider
from flutter_agent.security.scope import ProjectScope
from flutter_agent.planning.task_plan import build_plan
from flutter_agent.planning.workflow import WorkflowExecutor
from flutter_agent.skills.loader import load_skills
from flutter_agent.standards.loader import load_rules
from flutter_agent.standards.dependencies import validate_dependencies
from flutter_agent.tools.registry import ToolRegistry
from flutter_agent.reporting.report import DeliveryReport
from flutter_agent.reporting.audit import AuditLog
from flutter_agent.preflight import check_configuration
from flutter_agent.project.profile import detect_profile
from flutter_agent.project.memory import save_profile
from flutter_agent.project.overrides import apply_project_overrides
from flutter_agent.routing.router import route_task
from flutter_agent.state.migrations import ensure_state

app = typer.Typer(help="Governed coding agent for Flutter projects.")


def _save_report(root: Path, report: DeliveryReport) -> Path:
    directory = root / ".flutter-agent" / "reports"
    directory.mkdir(parents=True, exist_ok=True)
    path = directory / f"{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}.json"
    path.write_text(json.dumps(report.to_dict(), indent=2), encoding="utf-8")
    return path


@app.command()
def doctor(project: Path = typer.Option(Path.cwd(), exists=True, file_okay=False)) -> None:
    """Inspect a project without modifying it."""
    resolved = project.expanduser().resolve()
    config = load_agent_config(resolved)
    typer.echo(f"Project root: {resolved}")
    if (resolved / "pubspec.yaml").exists():
        typer.echo("Flutter project: detected")
        profile = apply_project_overrides(resolved, detect_profile(resolved))
        save_profile(resolved, profile)
        typer.echo(f"Architecture: {profile.architecture}")
        typer.echo(f"State management: {profile.state_management}")
        typer.echo(f"HTTP client: {profile.http_client}")
        typer.echo(f"Routing: {profile.routing}")
    else:
        typer.echo("Flutter project: not detected")
    for check in check_configuration(config):
        typer.echo(f"{'OK' if check.ok else 'FAIL'} [{check.name}] {check.message}")
    rules_path = resolved / ".flutter-agent" / "rules.toml"
    if rules_path.exists() and (resolved / "pubspec.yaml").exists():
        rules = load_rules(rules_path)
        findings = validate_dependencies(
            resolved / "pubspec.yaml",
            rules.approved_dependencies,
            rules.forbidden_dependencies,
        )
        for finding in findings:
            typer.echo(f"FAIL [dependencies] {finding}")


@app.command()
def run(
    task: str,
    project: Path = typer.Option(Path.cwd(), exists=True, file_okay=False),
    provider: Optional[str] = typer.Option(None, help="Model provider adapter"),
    model: Optional[str] = typer.Option(None, help="Provider model identifier"),
    max_steps: Optional[int] = typer.Option(None, min=1, max=100),
    budget_usd: Optional[float] = typer.Option(None, min=0.0, help="Maximum model spend for this run"),
    contract_file: Optional[Path] = typer.Option(None, exists=True, file_okay=True, dir_okay=False, help="TOML task contract"),
    workflow: bool = typer.Option(True, "--workflow/--single-agent", help="Run staged subagents or one agent"),
) -> None:
    """Run a bounded task against a project using the configured provider."""
    root = project.expanduser().resolve()
    ensure_state(root)
    audit = AuditLog(root)
    base_config = load_agent_config(root)
    contract = load_contract(contract_file.expanduser().resolve()) if contract_file else None
    routing = route_task(task) if not model and not base_config.provider.model else None
    routed_models = (model or base_config.provider.model,) if (model or base_config.provider.model) else routing.models
    # A zero-dollar run is explicitly free-tier only. Do not silently fall
    # through to a paid model after free providers are rate limited.
    if budget_usd == 0 and routing is not None:
        routed_models = tuple(candidate for candidate in routed_models if candidate.endswith(":free"))
        if not routed_models:
            raise typer.ClickException("No free routed model is available for this task")
    routed_model = routed_models[0]
    audit.record("run_started", task=task, models=list(routed_models), workflow=workflow)
    if routing is not None:
        typer.echo(f"Routing category: {routing.category}")
        typer.echo("Model fallback chain: " + " -> ".join(routed_models))
    else:
        typer.echo(f"Explicit model: {routed_model}")
    config = AgentConfig(
        project_root=root,
        provider=ProviderConfig(
            name=provider or base_config.provider.name,
            base_url=base_config.provider.base_url,
            model=routed_model,
            api_key_env=base_config.provider.api_key_env,
            timeout_seconds=base_config.provider.timeout_seconds,
            max_output_tokens=base_config.provider.max_output_tokens,
                retry_attempts=base_config.provider.retry_attempts,
                retry_backoff_seconds=base_config.provider.retry_backoff_seconds,
                circuit_failure_threshold=base_config.provider.circuit_failure_threshold,
                circuit_cooldown_seconds=base_config.provider.circuit_cooldown_seconds,
            input_per_million=base_config.provider.input_per_million,
            output_per_million=base_config.provider.output_per_million,
            supports_tools=base_config.provider.supports_tools,
            supports_structured_output=base_config.provider.supports_structured_output,
        ),
        max_steps=max_steps or base_config.max_steps,
        max_repair_attempts=base_config.max_repair_attempts,
        budget_usd=budget_usd if budget_usd is not None else base_config.budget_usd,
    )
    profile = apply_project_overrides(root, detect_profile(root))
    save_profile(root, profile)
    try:
        rules_path = root / ".flutter-agent" / "rules.toml"
        rules = load_rules(rules_path) if rules_path.exists() else None
        provider_configs = [
            ProviderConfig(
                name=config.provider.name,
                base_url=config.provider.base_url,
                model=candidate,
                api_key_env=config.provider.api_key_env,
                timeout_seconds=config.provider.timeout_seconds,
                max_output_tokens=config.provider.max_output_tokens,
                retry_attempts=config.provider.retry_attempts,
                retry_backoff_seconds=config.provider.retry_backoff_seconds,
                circuit_failure_threshold=config.provider.circuit_failure_threshold,
                circuit_cooldown_seconds=config.provider.circuit_cooldown_seconds,
                input_per_million=config.provider.input_per_million,
                output_per_million=config.provider.output_per_million,
                supports_tools=config.provider.supports_tools,
                supports_structured_output=config.provider.supports_structured_output,
            )
            for candidate in routed_models
        ]
        providers = tuple(
            ResilientProvider(
                create_provider(provider_config),
                retries=provider_config.retry_attempts,
                backoff_seconds=provider_config.retry_backoff_seconds,
                failure_threshold=provider_config.circuit_failure_threshold,
                cooldown_seconds=provider_config.circuit_cooldown_seconds,
            )
            for provider_config in provider_configs
        )
        provider_instance = providers[0] if len(providers) == 1 else FallbackProvider(providers)
        registry = ToolRegistry(ProjectScope(config.resolved_root()), rules)
        free_tier = routed_model.endswith(":free")
        ledger = CostLedger(
            config.budget_usd,
            input_per_million=0.0 if free_tier else config.provider.input_per_million,
            output_per_million=0.0 if free_tier else config.provider.output_per_million,
        )
        if workflow:
            skills = load_skills(root / ".flutter-agent" / "skills").select(task)
            plan = build_plan(task, skills, contract)
            orchestrator = SequentialOrchestrator(
                ProviderSubagentRunner(provider_instance, registry, max_steps=config.max_steps, ledger=ledger)
            )
            specs = [
                    SubagentSpec(stage.role, stage.prompt, stage.allowed_tools)
                    for stage in plan.stages
            ]
            workflow_result = WorkflowExecutor(orchestrator, config.max_repair_attempts).run(
                specs,
                task + f"\nDetected project profile: {profile}",
                lambda outputs: (
                    True,
                    "",
                ) if contract is None else (
                    (contract_result := validate_contract(root, contract)).passed,
                    "; ".join(contract_result.findings),
                ),
            )
            if not workflow_result.completed:
                report_path = _save_report(
                    root,
                    DeliveryReport(task, False, tuple(stage.role for stage in plan.stages), workflow_result.outputs, workflow_result.error),
                )
                typer.echo(f"Workflow incomplete: {workflow_result.error}")
                typer.echo(f"Report: {report_path}")
                audit.record("run_completed", completed=False, error=workflow_result.error)
                raise typer.Exit(code=1)
            report_path = _save_report(
                root,
                DeliveryReport(task, True, tuple(stage.role for stage in plan.stages), workflow_result.outputs),
            )
            typer.echo(workflow_result.outputs[-1] if workflow_result.outputs else "Workflow completed")
            typer.echo(f"Stages: {len(workflow_result.outputs)}; Repairs: {workflow_result.repairs}")
            typer.echo(f"Report: {report_path}")
            audit.record("run_completed", completed=True, stages=len(workflow_result.outputs), repairs=workflow_result.repairs)
            return
        result = AgentLoop(provider_instance, registry, max_steps=config.max_steps, ledger=ledger, contract=contract).run(task)
    except (ValueError, PermissionError, RuntimeError) as exc:
        raise typer.ClickException(str(exc)) from exc
    if result.completed:
        report_path = _save_report(root, DeliveryReport(task, True, ("single-agent",), (result.text or "",)))
        typer.echo(result.text or "Task completed")
        typer.echo(f"Steps: {result.steps}")
        typer.echo(f"Report: {report_path}")
        audit.record("run_completed", completed=True, steps=result.steps)
    else:
        report_path = _save_report(root, DeliveryReport(task, False, ("single-agent",), (result.text or "",), result.error))
        typer.echo(f"Task incomplete: {result.error}")
        typer.echo(f"Steps: {result.steps}")
        typer.echo(f"Report: {report_path}")
        audit.record("run_completed", completed=False, steps=result.steps, error=result.error)
        raise typer.Exit(code=1)


if __name__ == "__main__" and "_fallback_main" in globals():
    _fallback_main()

