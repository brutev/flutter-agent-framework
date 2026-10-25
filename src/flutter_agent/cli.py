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
from flutter_agent.providers.registry import create_provider
from flutter_agent.providers.fallback import FallbackProvider
from flutter_agent.providers.resilience import ResilientProvider
from flutter_agent.security.scope import ProjectScope
from flutter_agent.security.secrets import redact_secrets
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
from flutter_agent.playbooks.registry import PlaybookRegistry
from flutter_agent.tasks import (
    BudgetLimits,
    LifecyclePhase,
    PermissionPolicy,
    PlanStep,
    TaskLifecycle,
    TaskStatus,
    VerificationRequirement,
    create_task,
)
from flutter_agent.verification.engine import VerificationEngine, select_flutter_checks
from flutter_agent.verification.models import VerificationReport

app = typer.Typer(help="Governed coding agent for Flutter projects.")


def _acceptance_criteria(contract) -> tuple[str, ...]:
    if contract is None:
        return ("Complete the stated user goal without unsupported success claims.",)
    return tuple(
        [f"Required file: {path}" for path in contract.required_files]
        + [f"Required symbol: {symbol}" for symbol in contract.required_symbols]
        + [f"Forbidden content absent: {value}" for value in contract.forbidden_content]
    ) or ("Complete the stated user goal.",)


def _finish_lifecycle(task_record, lifecycle: TaskLifecycle, verification_report, outcome: str):
    if verification_report is None:
        verification_status = TaskStatus.FAILED
        evidence = ()
        verification_outcome = outcome
    else:
        verification_status = TaskStatus.VERIFIED if verification_report.verified else (
            TaskStatus.FAILED if verification_report.status.value == "FAILED" else TaskStatus.UNVERIFIED
        )
        evidence = (f"verification:{verification_report.source_snapshot}",)
        verification_outcome = verification_report.summary
    task_record = lifecycle.transition(
        task_record,
        LifecyclePhase.VERIFY,
        verification_status,
        verification_outcome,
        evidence,
    )
    review_status = TaskStatus.REVIEW_REQUIRED if verification_status is TaskStatus.VERIFIED else verification_status
    task_record = lifecycle.transition(
        task_record,
        LifecyclePhase.REVIEW,
        review_status,
        "Independent review is required before merge" if review_status is TaskStatus.REVIEW_REQUIRED else outcome,
    )
    return lifecycle.transition(
        task_record,
        LifecyclePhase.DELIVER,
        review_status,
        "Delivery report generated from recorded execution data",
    )


def _save_report(root: Path, report: DeliveryReport) -> Path:
    directory = root / ".flutter-agent" / "reports"
    directory.mkdir(parents=True, exist_ok=True)
    path = directory / f"{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}.json"
    serialized = json.dumps(report.to_dict(), indent=2)
    path.write_text(redact_secrets(serialized), encoding="utf-8")
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
    task_routing = route_task(task)
    model_routing = task_routing if not model and not base_config.provider.model else None
    routed_models = (model or base_config.provider.model,) if (model or base_config.provider.model) else task_routing.models
    # A zero-dollar run is explicitly free-tier only. Do not silently fall
    # through to a paid model after free providers are rate limited.
    if budget_usd == 0 and model_routing is not None:
        routed_models = tuple(candidate for candidate in routed_models if candidate.endswith(":free"))
        if not routed_models:
            raise typer.ClickException("No free routed model is available for this task")
    routed_model = routed_models[0]
    audit.record("run_started", task=task, models=list(routed_models), workflow=workflow)
    if model_routing is not None:
        typer.echo(f"Routing category: {task_routing.category}")
        typer.echo(f"Playbook: {task_routing.playbook} ({task_routing.rationale})")
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
        role_models=base_config.role_models,
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
        role_providers = {}
        for role, role_model in config.role_models.items():
            role_config = config.provider.model_copy(update={"model": role_model})
            role_providers[role] = ResilientProvider(
                create_provider(role_config),
                retries=role_config.retry_attempts,
                backoff_seconds=role_config.retry_backoff_seconds,
                failure_threshold=role_config.circuit_failure_threshold,
                cooldown_seconds=role_config.circuit_cooldown_seconds,
            )
        registry = ToolRegistry(ProjectScope(config.resolved_root()), rules)
        configured_models = tuple(routed_models) + tuple(config.role_models.values())
        free_tier = all(candidate.endswith(":free") for candidate in configured_models)
        ledger = CostLedger(
            config.budget_usd,
            input_per_million=0.0 if free_tier else config.provider.input_per_million,
            output_per_million=0.0 if free_tier else config.provider.output_per_million,
        )
        verification_engine = VerificationEngine(root)
        verification_checks = select_flutter_checks(root, task)
        lifecycle = TaskLifecycle()
        task_record = create_task(
            task,
            root,
            _acceptance_criteria(contract),
            budget=BudgetLimits(config.budget_usd, config.max_steps, config.max_repair_attempts),
        )
        task_record = lifecycle.transition(
            task_record,
            LifecyclePhase.CLASSIFY,
            TaskStatus.IN_PROGRESS,
            task_routing.rationale,
            task_type=task_routing.task_type,
            risk=task_routing.risk,
        )
        if workflow:
            skills = load_skills(root / ".flutter-agent" / "skills").select(task)
            playbook = PlaybookRegistry().get(task_routing.playbook)
            plan = build_plan(task, skills, contract, playbook, task_routing.rationale)
            plan_steps = tuple(
                PlanStep(
                    stage.role,
                    stage.prompt,
                    dependencies=(plan.stages[index - 1].role,) if index else (),
                    acceptance_criteria=playbook.acceptance_criteria,
                )
                for index, stage in enumerate(plan.stages)
            )
            task_record = lifecycle.transition(
                task_record,
                LifecyclePhase.PLAN,
                TaskStatus.PLANNED,
                f"Selected {playbook.name} playbook with {len(plan.stages)} stages",
                plan=plan_steps,
                permissions=PermissionPolicy(
                    tuple(sorted(set().union(*(stage.allowed_tools for stage in plan.stages)))),
                    all("write_file" not in stage.allowed_tools for stage in plan.stages),
                ),
                verification_requirements=tuple(
                    VerificationRequirement(check.name, check.argv, check.required)
                    for check in verification_checks
                ),
            )
            task_record = lifecycle.transition(
                task_record,
                LifecyclePhase.EXECUTE,
                TaskStatus.IN_PROGRESS,
                "Workflow execution started",
            )
            orchestrator = SequentialOrchestrator(
                ProviderSubagentRunner(
                    provider_instance,
                    registry,
                    max_steps=config.max_steps,
                    ledger=ledger,
                    reserve_output_tokens=config.provider.max_output_tokens,
                    role_providers=role_providers,
                )
            )
            specs = [
                SubagentSpec(stage.role, stage.prompt, stage.allowed_tools)
                for stage in plan.stages
            ]
            verification_reports: list[VerificationReport] = []

            def verify_workflow(_outputs: tuple[str, ...]) -> tuple[bool, str]:
                report = verification_engine.verify(verification_checks, contract)
                verification_reports.append(report)
                audit.record("verification_completed", **report.to_dict())
                return report.verified, report.summary

            workflow_result = WorkflowExecutor(orchestrator, config.max_repair_attempts).run(
                specs,
                task + f"\nDetected project profile: {profile}",
                verify_workflow,
            )
            verification_report = verification_reports[-1] if verification_reports else None
            if not workflow_result.completed:
                task_record = _finish_lifecycle(
                    task_record,
                    lifecycle,
                    verification_report,
                    workflow_result.error or "Workflow execution failed",
                )
                report_path = _save_report(
                    root,
                    DeliveryReport.from_task(
                        task_record,
                        completed=False,
                        stages=tuple(stage.role for stage in plan.stages),
                        outputs=workflow_result.outputs,
                        error=workflow_result.error,
                        verification=verification_report.to_dict() if verification_report else None,
                    ),
                )
                typer.echo(f"Workflow incomplete: {workflow_result.error}")
                typer.echo(f"Report: {report_path}")
                audit.record("run_completed", completed=False, status=task_record.status.value, error=workflow_result.error)
                raise typer.Exit(code=1)
            task_record = _finish_lifecycle(task_record, lifecycle, verification_report, "Workflow completed")
            report_path = _save_report(
                root,
                DeliveryReport.from_task(
                    task_record,
                    completed=True,
                    stages=tuple(stage.role for stage in plan.stages),
                    outputs=workflow_result.outputs,
                    verification=verification_report.to_dict() if verification_report else None,
                ),
            )
            typer.echo(workflow_result.outputs[-1] if workflow_result.outputs else "Workflow completed")
            typer.echo(f"Stages: {len(workflow_result.outputs)}; Repairs: {workflow_result.repairs}")
            typer.echo(f"Report: {report_path}")
            audit.record("run_completed", completed=True, status=task_record.status.value, stages=len(workflow_result.outputs), repairs=workflow_result.repairs)
            return
        task_record = lifecycle.transition(
            task_record,
            LifecyclePhase.PLAN,
            TaskStatus.PLANNED,
            "Selected bounded single-agent execution",
            plan=(PlanStep("single-agent", "Execute the scoped task with governed tools"),),
            permissions=PermissionPolicy(tuple(sorted(tool["function"]["name"] for tool in registry.schemas()))),
            verification_requirements=tuple(
                VerificationRequirement(check.name, check.argv, check.required)
                for check in verification_checks
            ),
        )
        task_record = lifecycle.transition(
            task_record,
            LifecyclePhase.EXECUTE,
            TaskStatus.IN_PROGRESS,
            "Single-agent execution started",
        )
        result = AgentLoop(provider_instance, registry, max_steps=config.max_steps, ledger=ledger, contract=contract, reserve_output_tokens=config.provider.max_output_tokens).run(task)
    except (ValueError, PermissionError, RuntimeError) as exc:
        raise typer.ClickException(str(exc)) from exc
    verification_report = verification_engine.verify(verification_checks, contract) if result.completed else None
    if verification_report is not None:
        audit.record("verification_completed", **verification_report.to_dict())
    if result.completed and verification_report is not None and verification_report.verified:
        task_record = _finish_lifecycle(task_record, lifecycle, verification_report, "Execution completed")
        report_path = _save_report(
            root,
            DeliveryReport.from_task(
                task_record,
                completed=True,
                stages=("single-agent",),
                outputs=(result.text or "",),
                verification=verification_report.to_dict(),
            ),
        )
        typer.echo(result.text or "Task completed")
        typer.echo(f"Steps: {result.steps}")
        typer.echo(f"Report: {report_path}")
        audit.record("run_completed", completed=True, status=task_record.status.value, steps=result.steps)
    else:
        verification_error = verification_report.summary if verification_report is not None else result.error
        task_record = _finish_lifecycle(
            task_record,
            lifecycle,
            verification_report,
            verification_error or "Execution failed",
        )
        report_path = _save_report(
            root,
            DeliveryReport.from_task(
                task_record,
                completed=False,
                stages=("single-agent",),
                outputs=(result.text or "",),
                error=verification_error,
                verification=verification_report.to_dict() if verification_report else None,
            ),
        )
        typer.echo(f"Task incomplete: {verification_error}")
        typer.echo(f"Steps: {result.steps}")
        typer.echo(f"Report: {report_path}")
        audit.record("run_completed", completed=False, status=task_record.status.value, steps=result.steps, error=verification_error)
        raise typer.Exit(code=1)


if __name__ == "__main__" and "_fallback_main" in globals():
    _fallback_main()

