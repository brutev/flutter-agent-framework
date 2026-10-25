# Engineering audit

Audit date: 2026-10-24
Audited revision: `b771892` plus the uncommitted Milestone 1 changes described below
Baseline: clean `main`; `python3 -m pytest -q` initially failed collection because the `src/` package was not importable; `PYTHONPATH=src python3 -m pytest -q` passed 64 tests.

## Scope and execution trace

The audit covered all tracked source and test files, `README.md`, `pyproject.toml`, `.gitignore`, `.flutter-agent/rules.toml`, Git state, provider adapters, routing, planning, agent loops, tools, contracts, cost handling, repair, persisted state, reports, and CLI behavior. The repository has no CI workflow.

A real `flutter-agent run` follows this path:

1. `cli.run` creates project-local state, loads configuration and an optional contract, routes a model, profiles the Flutter project, and constructs resilient/fallback providers.
2. Workflow mode builds four fixed stages (analyst, implementer, tester, reviewer). `SequentialOrchestrator` calls `ProviderSubagentRunner`, which runs a new bounded `AgentLoop` with role-specific tool grants.
3. `AgentLoop` sends messages to the provider, executes returned tool calls through `ToolRegistry`, and stops on a response without tool calls or its step limit.
4. Before this milestone, the workflow verification callback returned success unconditionally when no contract was supplied. The tester's claimed checks and model prose were not evidence. Single-agent mode likewise treated a tool-free response as completed.
5. After this milestone, the CLI independently selects and runs deterministic checks through `VerificationEngine`. It records command arguments, working directory, exit code, duration, bounded/redacted output, status, acceptance findings, and final source snapshot. Only `VERIFIED` reaches the successful CLI path.

Provider capability profiles, security scans, dependency policy, state migrations, OCR support, and the standalone `RepairController` exist but are not all connected to the main execution path. `ModelCatalog` is currently tested infrastructure rather than an enforced fallback gate. The workflow repair path reruns the entire four-stage workflow rather than a scoped diagnosis/repair stage.

## Findings

### AUD-001 — Critical — completion bypassed verification (remediated)

- Evidence: the original `cli.run` callback returned `(True, "")` whenever `contract is None`; `AgentLoop` returned `completed=True` for any provider response without tool calls.
- Reproduction: run any workflow without `--contract-file`; a model can return completion prose without running `flutter analyze` or tests and receive a successful report.
- Impact: false-positive task completion and untrustworthy delivery reports.
- Remediation: `VerificationEngine`, typed check/report statuses, mandatory evidence, task-aware Flutter checks, source snapshots, and CLI integration for workflow and single-agent paths.
- Tests: `test_missing_verification_evidence_cannot_pass`, `test_failed_command_cannot_pass_without_contract`, `test_model_success_claim_cannot_override_failed_verification`, and `test_contract_without_command_evidence_remains_unverified`.

### AUD-002 — High — blocked checks were indistinguishable from failures (remediated)

- Evidence: `FlutterTools.verify` returned `ToolResult(False, error=...)` for both missing executables and timeouts; reports contained no command evidence.
- Reproduction: run verification where `flutter` is unavailable.
- Impact: operators could not distinguish a bad project from an incapable environment.
- Remediation: `CheckStatus` separates `PASSED`, `FAILED`, and `BLOCKED`; blocked mandatory evidence produces `UNVERIFIED`.
- Tests: `test_blocked_command_is_unverified_not_successful`.

### AUD-003 — High — verification evidence could be reused after source changes (remediated)

- Evidence: prior reports contained only model stage outputs and a Boolean `completed` value.
- Reproduction: complete a run, edit a source file, and inspect the old report; it had no revision binding.
- Impact: stale evidence could be presented for a different project state.
- Remediation: deterministic SHA-256 source snapshots and `VerificationReport.is_current`.
- Tests: `test_new_source_change_invalidates_old_verification`.

### AUD-004 — High — delivery reports could persist secret-like model output (remediated with limitations)

- Evidence: `_save_report` wrote `json.dumps(report.to_dict())` directly, including provider text and command output.
- Reproduction: put `api_key=abcdefghijklmnop` in a stage output and save a report.
- Impact: credentials echoed by a tool or provider could be persisted below the target project.
- Remediation: serialized reports are passed through the existing redactor; verification output is bounded and redacted.
- Tests: `test_delivery_report_redacts_secret_like_output`.
- Limitation: pattern-based redaction cannot identify every proprietary or sensitive project value. Reports should not contain unnecessary source content.

### AUD-005 — Medium — `doctor` violated its read-only contract (remediated)

- Evidence: `doctor` called `save_profile`, creating `.flutter-agent/project_profile.json`.
- Reproduction: run `doctor` on a Flutter project with no `.flutter-agent` directory.
- Impact: inspection unexpectedly modified the target repository.
- Remediation: profile persistence was removed from `doctor` and retained only for `run`.
- Tests: `test_doctor_is_read_only`.

### AUD-006 — Medium — checkout tests did not run as documented (remediated)

- Evidence: `python3 -m pytest -q` produced 34 import-collection errors because `flutter_agent` under `src/` was not importable.
- Reproduction: run the documented test command without first installing the package.
- Impact: poor first-run experience and a misleading baseline.
- Remediation: configure pytest's `pythonpath = ["src"]`; installation remains the supported packaged workflow.
- Tests: the final suite runs directly from the checkout.

### AUD-007 — High — filesystem authorization has a time-of-check/time-of-use window (partially remediated)

- Evidence: `ProjectScope.resolve` resolves and validates a path, then `FilesystemTools` opens it in a separate operation. Existing parent symlink escapes are rejected, but a concurrently swapped path can race the check.
- Reproduction: requires adversarial concurrent replacement of a validated directory with a symlink between resolution and file access.
- Impact: a hostile local process with write access to the project may redirect a read or write outside the root.
- Remediation: writes now use a same-directory temporary file, flush and `fsync`, then atomically replace the target. Remaining work requires descriptor-relative no-follow operations and explicit concurrency/version checks.
- Existing tests: parent traversal, final symlink overwrite, external directory symlink writes, and security-scan symlink detection. Race resistance remains unverified.

### AUD-008 — High — budget enforcement occurs after provider spend (partially remediated)

- Evidence: `AgentLoop` checks `ledger.exceeded` before later steps but records usage only after a provider call; `can_reserve` is unused.
- Reproduction: set a small positive budget and return usage whose cost exceeds the remaining amount in one call.
- Impact: a task can exceed its configured monetary budget by at least one request; fallbacks and repair stages share no pre-call token reservation.
- Remediation: the loop now estimates input tokens and reserves configured maximum output cost before every provider call and finalization. Remaining work is provider-reported per-model pricing and coordinated reservations for future concurrent execution.
- Required tests: first-call overspend, fallback accounting, zero-cost routes, and repair-budget exhaustion.

### AUD-009 — High — fallback capability and error policies are not fully enforced (partially remediated)

- Evidence: `ModelCatalog` is not used by `cli.run`; all routed fallback models inherit one provider capability/pricing configuration. `FallbackProvider` tries the next model for broad `RuntimeError` and `ValueError` categories.
- Reproduction: configure a fallback without tool support or trigger a permanent authentication/configuration error.
- Impact: incompatible requests, misleading cost estimates, and avoidable latency.
- Remediation: typed failure categories distinguish permanent, transient, rate-limit, timeout, malformed, capability, and cancelled outcomes; permanent failures are not retried. Role-specific models are supported. Per-model capability and price enforcement before fallback remains open.
- Required tests: tool/structured-output mismatch, permanent error without retry, rate-limit fallback, and context-limit mismatch.

### AUD-010 — Medium — tool-call validation is structural but not schema-complete (remediated for current tools)

- Evidence: normalization assumes nested function fields, and `ToolRegistry.execute` relies on Python keyword binding rather than validating JSON Schema, duplicate call IDs, sizes, or argument types.
- Reproduction: return malformed nested tool data or oversized values from a provider.
- Impact: confusing provider failures, excessive memory/log output, and inconsistent adapter behavior.
- Remediation: the registry now validates required, unknown, and typed arguments, bounds string payloads, and the agent loop rejects empty or duplicate call IDs before dispatch. Future nested tool schemas will require recursive validation.

### AUD-011 — Medium — legacy workflow repair remains broad (partially remediated)

- Evidence: `WorkflowExecutor` reruns every stage and passes only a failure string; it does not provide changed-file context or target affected checks.
- Reproduction: make only `flutter test` fail; the analyst, implementer, tester, and reviewer all run again.
- Impact: unnecessary cost/latency and a greater chance of unrelated changes.
- Remediation: `GovernedRepairLoop` supplies failed evidence, acceptance criteria, changed files, snapshot, and attempt number; re-verifies affected checks; enforces a bound; and stops identical failures without a new snapshot. The legacy `WorkflowExecutor` still reruns all stages and should migrate to this loop.

### AUD-012 — Medium — observability and cancellation are incomplete (open)

- Evidence: reports now contain verification timing, but provider/stage latency, retry counts, token usage, estimated cost, cancellation, and failure categories are not persisted end-to-end.
- Impact: performance and cost regressions cannot be benchmarked reliably.
- Proposed remediation: typed per-stage telemetry and cooperative cancellation propagated through providers, orchestration, commands, and repair.

### AUD-013 — Medium — no CI quality gate or benchmark harness exists (remediated for deterministic components)

- Evidence: no `.github/workflows` files or benchmark directory are present.
- Impact: regressions depend on local discipline, and improvement claims cannot be compared reproducibly.
- Remediation: CI runs tests and the ten-scenario governance benchmark on Python 3.11–3.13 and stores JSON artifacts. Real Flutter application/provider benchmarks remain open and are not represented by the component success rate.

## Security boundary assessment

All exposed filesystem tool paths pass through `ProjectScope`; existing symlinks that resolve outside the root are rejected. Command execution uses fixed argument vectors with no shell. Current command timeouts are bounded and outputs are capped. Read-only role grants exclude write tools. These are useful controls, not a complete sandbox: local filesystem races, subprocess descendants after timeout, sensitive non-secret content in reports, and budget propagation remain documented limitations.

Untrusted repository content is currently sent to model context as data through tools, but the framework has no explicit instruction-origin labeling or prompt-injection policy enforcement. Model instructions cannot directly bypass the deterministic tool registry; they can still influence permitted writes. This needs adversarial benchmark coverage.

## pstack reference assessment

pstack's useful ideas are explicit playbook steps, role/model separation, observable skipped steps, project-specific verification harnesses, and parallelism only where work is independent. This milestone adopts the evidence-first verification principle and task-aware check selection. It deliberately does not copy pstack's large skill surface or parallel orchestration: the current framework has not yet earned that complexity through benchmark evidence.

## Milestone result and continuation

Milestone 1 completed in this session:

- audited the complete repository and traced the executable CLI path;
- established and documented the baseline;
- removed the no-contract verification bypass;
- added typed, machine-readable, snapshot-bound verification evidence;
- distinguished failed and blocked commands;
- added task-aware Flutter format/analyze/test and conditional Android checks;
- made workflow repair stop on identical failures;
- made `doctor` read-only and delivery reports redacted;
- added regression and adversarial path tests; and
- updated documentation to actual behavior.

Subsequent work completed typed lifecycle records, seven structured playbooks, task-aware planning, lifecycle-derived delivery reports, role-specific models, pre-call budget reservation, snapshot-aware repair, recurring-failure proposals, atomic file replacement, typed provider failures, CI, and the deterministic benchmark suite.

Remaining priorities are real Flutter fixture benchmarks, descriptor-relative filesystem hardening, full capability-aware fallback, cancellation propagation, and migration of the legacy workflow executor to the governed repair loop. Safe parallel execution is intentionally deferred: the component benchmark does not show that parallel writes would improve success enough to justify conflict and cancellation complexity.
