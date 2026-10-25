from __future__ import annotations

from flutter_agent.playbooks.models import Playbook, PlaybookStage
from flutter_agent.tasks.models import TaskType
from flutter_agent.verification.models import CheckSpec

READ = frozenset({"list_files", "read_file", "search_code"})
WRITE = READ | {"write_file"}
VERIFY = READ | {"verify"}


def _flutter_checks() -> tuple[CheckSpec, ...]:
    return (
        CheckSpec("dart_format", ("dart", "format", "--output=none", "--set-exit-if-changed", ".")),
        CheckSpec("flutter_analyze", ("flutter", "analyze"), timeout_seconds=180),
        CheckSpec("flutter_test", ("flutter", "test"), timeout_seconds=300),
    )


def builtin_playbooks() -> tuple[Playbook, ...]:
    checks = _flutter_checks()
    return (
        Playbook(
            "investigate",
            "Repository exploration or root-cause analysis without requested implementation.",
            (TaskType.QUESTION, TaskType.EXPLORATION),
            ("user goal", "project root", "scope"),
            (
                PlaybookStage("analyst", "Trace only the relevant execution path and collect concrete evidence.", READ),
                PlaybookStage("reviewer", "Check that findings are supported and no files were modified.", READ),
            ),
            ("Findings cite concrete project evidence.", "Project source remains unchanged."),
            (),
            "Report missing access or evidence as blocked; do not modify files to manufacture evidence.",
            ("investigation report",),
        ),
        Playbook(
            "bug_fix",
            "A concrete defect has expected and observed behavior.",
            (TaskType.BUG_FIX, TaskType.BUILD_REPAIR),
            ("reproduction", "expected behavior", "project root"),
            (
                PlaybookStage("analyst", "Reproduce the defect and identify its root cause.", READ | {"verify"}),
                PlaybookStage("implementer", "Apply the smallest justified fix and add a regression test.", WRITE),
                PlaybookStage("tester", "Run focused and regression checks.", VERIFY),
                PlaybookStage("reviewer", "Review the actual diff independently against the defect.", VERIFY),
            ),
            ("The defect is reproduced before the fix.", "A regression test fails before and passes after."),
            checks,
            "Diagnose the failed mandatory check, make one bounded repair, and re-run affected checks.",
            ("reproduction evidence", "regression test", "verification report", "review findings"),
        ),
        Playbook(
            "feature",
            "New observable behavior is requested.",
            (TaskType.FEATURE, TaskType.ARCHITECTURE),
            ("acceptance criteria", "project root", "scope"),
            (
                PlaybookStage("analyst", "Inspect existing patterns and clarify acceptance boundaries.", READ),
                PlaybookStage("architect", "Choose the smallest compatible design and record trade-offs.", READ),
                PlaybookStage("implementer", "Implement the bounded feature and tests.", WRITE),
                PlaybookStage("tester", "Exercise acceptance criteria and regressions.", VERIFY),
                PlaybookStage("reviewer", "Review the actual diff for correctness, security, and scope.", VERIFY),
            ),
            ("Every mandatory acceptance criterion has evidence.", "Existing behavior remains covered."),
            checks,
            "Stop on ambiguous mandatory criteria; otherwise repair only evidence-backed failures.",
            ("design decision", "tests", "verification report", "review findings"),
        ),
        Playbook(
            "refactor",
            "Structure should change while behavior remains stable.",
            (TaskType.REFACTOR,),
            ("preserved behavior", "regression risks", "scope"),
            (
                PlaybookStage("analyst", "Define behavior invariants and blast radius.", READ),
                PlaybookStage("implementer", "Make bounded structural changes without feature additions.", WRITE),
                PlaybookStage("tester", "Prove preserved behavior with focused and regression checks.", VERIFY),
                PlaybookStage("reviewer", "Reject behavior drift and unnecessary abstraction.", VERIFY),
            ),
            ("Declared behavior is unchanged.", "No unrelated feature work is included."),
            checks,
            "Revert the proposed direction conceptually and choose a smaller refactor if invariants cannot be proven.",
            ("invariant list", "verification report", "diff review"),
        ),
        Playbook(
            "code_review",
            "An existing diff or change set needs independent review.",
            (TaskType.EXPLORATION, TaskType.SECURITY),
            ("requirements", "acceptance criteria", "actual diff"),
            (PlaybookStage("reviewer", "Find concrete correctness, security, performance, and coverage defects.", VERIFY),),
            ("Every finding has a location, impact, and evidence.", "No speculative finding is presented as fact."),
            (),
            "Mark areas unverified when required runtime evidence is unavailable.",
            ("review findings",),
        ),
        Playbook(
            "flutter_quality",
            "Flutter-specific lifecycle, state, navigation, async, accessibility, or platform behavior is central.",
            (TaskType.BUG_FIX, TaskType.FEATURE, TaskType.REFACTOR),
            ("Flutter project profile", "affected widgets or state", "acceptance criteria"),
            (
                PlaybookStage("analyst", "Inspect widget lifecycle, state transitions, async work, and disposal.", READ),
                PlaybookStage("implementer", "Apply Flutter-native patterns with explicit UI states.", WRITE),
                PlaybookStage("tester", "Run widget, state, and platform-relevant checks.", VERIFY),
                PlaybookStage("reviewer", "Review accessibility, navigation, resources, and edge states.", VERIFY),
            ),
            ("Loading, error, empty, and success behavior are intentional.", "Resources and subscriptions are disposed."),
            checks,
            "Use focused widget/state reproduction; do not add packages merely to bypass a design issue.",
            ("Flutter quality findings", "tests", "verification report"),
        ),
        Playbook(
            "release_readiness",
            "A requested scope must be assessed for release without publishing or deployment.",
            (TaskType.BUILD_REPAIR, TaskType.EXPLORATION),
            ("release scope", "verification results", "target platforms"),
            (
                PlaybookStage("analyst", "Inspect release configuration, generated artifacts, and blockers.", READ),
                PlaybookStage("tester", "Run permitted release-relevant checks.", VERIFY),
                PlaybookStage("reviewer", "Confirm unresolved risks and authorization boundaries.", VERIFY),
            ),
            ("All requested targets have evidence or explicit blockers.", "No publish or deploy action occurs."),
            checks,
            "Report blocked platform checks honestly and request authorization before any external release action.",
            ("release-readiness report", "verification report"),
        ),
    )


class PlaybookRegistry:
    def __init__(self, playbooks: tuple[Playbook, ...] | None = None):
        entries = playbooks if playbooks is not None else builtin_playbooks()
        self._playbooks = {playbook.name: playbook for playbook in entries}
        if len(self._playbooks) != len(entries):
            raise ValueError("Duplicate playbook name")

    def get(self, name: str) -> Playbook:
        try:
            return self._playbooks[name]
        except KeyError as exc:
            raise ValueError(f"Unknown playbook: {name}") from exc

    def all(self) -> tuple[Playbook, ...]:
        return tuple(self._playbooks.values())
