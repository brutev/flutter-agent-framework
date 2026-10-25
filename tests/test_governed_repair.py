import subprocess

from flutter_agent.repair.loop import GovernedRepairLoop
from flutter_agent.verification.engine import VerificationEngine
from flutter_agent.verification.models import CheckSpec


def report(tmp_path, return_code):
    executor = lambda *_: subprocess.CompletedProcess(("flutter", "test"), return_code, "", "failure" if return_code else "")
    return VerificationEngine(tmp_path, executor=executor).verify((CheckSpec("flutter_test", ("flutter", "test")),))


def test_governed_repair_reverifies_only_affected_checks(tmp_path) -> None:
    calls = []
    result = GovernedRepairLoop(max_attempts=2).run(
        report(tmp_path, 1),
        ("Regression passes",),
        ("lib/login.dart",),
        lambda context: calls.append(context) or "fixed test",
        lambda affected: report(tmp_path, 0),
    )
    assert result.report.verified
    assert result.attempts[0].affected_checks == ("flutter_test",)
    assert calls[0].acceptance_criteria == ("Regression passes",)


def test_governed_repair_stops_identical_failure_without_new_snapshot(tmp_path) -> None:
    initial = report(tmp_path, 1)
    result = GovernedRepairLoop(max_attempts=3).run(
        initial,
        (),
        (),
        lambda _context: "no effective change",
        lambda _affected: report(tmp_path, 1),
    )
    assert not result.report.verified
    assert len(result.attempts) == 1
    assert "Repeated failure" in (result.stopped_reason or "")
