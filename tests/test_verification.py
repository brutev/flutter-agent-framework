from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import subprocess

from flutter_agent.agents.orchestrator import OrchestrationResult
from flutter_agent.contracts.model import TaskContract
from flutter_agent.planning.workflow import WorkflowExecutor
from flutter_agent.verification.engine import VerificationEngine, select_flutter_checks
from flutter_agent.verification.models import CheckSpec, CheckStatus, VerificationStatus


def completed(returncode: int, stdout: str = "", stderr: str = "") -> subprocess.CompletedProcess[str]:
    return subprocess.CompletedProcess(("flutter", "test"), returncode, stdout, stderr)


def flutter_project(tmp_path: Path) -> Path:
    (tmp_path / "pubspec.yaml").write_text("name: example\n", encoding="utf-8")
    (tmp_path / "lib").mkdir()
    (tmp_path / "lib" / "main.dart").write_text("void main() {}\n", encoding="utf-8")
    return tmp_path


def test_missing_verification_evidence_cannot_pass(tmp_path: Path) -> None:
    report = VerificationEngine(tmp_path).verify(())
    assert report.status is VerificationStatus.UNVERIFIED
    assert not report.verified


def test_failed_command_cannot_pass_without_contract(tmp_path: Path) -> None:
    engine = VerificationEngine(tmp_path, executor=lambda *_: completed(1, stderr="tests failed"))
    report = engine.verify((CheckSpec("flutter_test", ("flutter", "test")),), contract=None)
    assert report.status is VerificationStatus.FAILED
    assert report.checks[0].status is CheckStatus.FAILED
    assert report.checks[0].exit_code == 1


def test_blocked_command_is_unverified_not_successful(tmp_path: Path) -> None:
    def missing(*_args):
        raise FileNotFoundError("flutter executable was not found")

    report = VerificationEngine(tmp_path, executor=missing).verify(
        (CheckSpec("flutter_test", ("flutter", "test")),)
    )
    assert report.status is VerificationStatus.UNVERIFIED
    assert report.checks[0].status is CheckStatus.BLOCKED
    assert report.checks[0].exit_code is None


def test_contract_cannot_override_failed_command(tmp_path: Path) -> None:
    (tmp_path / "lib").mkdir()
    (tmp_path / "lib" / "login.dart").write_text("class LoginCubit {}", encoding="utf-8")
    contract = TaskContract(("lib/login.dart",), ("LoginCubit",))
    engine = VerificationEngine(tmp_path, executor=lambda *_: completed(1))
    report = engine.verify((CheckSpec("flutter_test", ("flutter", "test")),), contract)
    assert not report.verified


@dataclass
class SuccessfulModelWorkflow:
    calls: int = 0

    def run(self, _specs, _context):
        self.calls += 1
        return OrchestrationResult(True, ("The model claims the task succeeded",))


def test_model_success_claim_cannot_override_failed_verification(tmp_path: Path) -> None:
    engine = VerificationEngine(tmp_path, executor=lambda *_: completed(1))
    check = (CheckSpec("flutter_test", ("flutter", "test")),)
    result = WorkflowExecutor(SuccessfulModelWorkflow(), max_repairs=0).run(
        [], "fix bug", lambda _outputs: (
            (report := engine.verify(check)).verified,
            report.summary,
        )
    )
    assert not result.completed


def test_repair_reruns_affected_check(tmp_path: Path) -> None:
    executions = 0

    def executor(*_args):
        nonlocal executions
        executions += 1
        return completed(1 if executions == 1 else 0)

    engine = VerificationEngine(tmp_path, executor=executor)
    check = (CheckSpec("flutter_test", ("flutter", "test")),)

    def verify(_outputs):
        report = engine.verify(check)
        return report.verified, report.summary

    workflow = SuccessfulModelWorkflow()
    result = WorkflowExecutor(workflow, max_repairs=1).run([], "fix bug", verify)
    assert result.completed
    assert result.repairs == 1
    assert executions == 2
    assert workflow.calls == 2


def test_new_source_change_invalidates_old_verification(tmp_path: Path) -> None:
    project = flutter_project(tmp_path)
    engine = VerificationEngine(project, executor=lambda *_: completed(0))
    report = engine.verify((CheckSpec("flutter_test", ("flutter", "test")),))
    assert report.verified
    assert report.is_current(project)
    (project / "lib" / "main.dart").write_text("void main() { print('changed'); }\n", encoding="utf-8")
    assert not report.is_current(project)


def test_changed_directory_symlink_invalidates_old_verification(tmp_path: Path) -> None:
    first = tmp_path / "first"
    second = tmp_path / "second"
    project = tmp_path / "project"
    first.mkdir()
    second.mkdir()
    project.mkdir()
    link = project / "linked"
    link.symlink_to(first, target_is_directory=True)
    engine = VerificationEngine(project, executor=lambda *_: completed(0))
    report = engine.verify((CheckSpec("flutter_test", ("flutter", "test")),))
    link.unlink()
    link.symlink_to(second, target_is_directory=True)
    assert not report.is_current(project)


def test_flutter_check_selection_is_task_aware(tmp_path: Path) -> None:
    project = flutter_project(tmp_path)
    assert select_flutter_checks(project, "Summarize the app") == ()
    names = [check.name for check in select_flutter_checks(project, "Fix the login bug")]
    assert names == ["dart_format", "flutter_analyze", "flutter_test"]
    (project / "android").mkdir()
    android_names = [check.name for check in select_flutter_checks(project, "Fix Android APK build")]
    assert android_names[-1] == "flutter_build_apk_debug"


def test_contract_without_command_evidence_remains_unverified(tmp_path: Path) -> None:
    (tmp_path / "required.dart").write_text("class Required {}", encoding="utf-8")
    report = VerificationEngine(tmp_path).verify(
        (), TaskContract(("required.dart",), ("Required",))
    )
    assert report.status is VerificationStatus.UNVERIFIED
