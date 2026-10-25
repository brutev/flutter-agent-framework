# Flutter Agent Framework

Python framework for governed, provider-agnostic Flutter development. The
orchestration layer is Python; generated and maintained applications continue
to use the native Dart and Flutter toolchain.

The current implementation provides OpenRouter, OpenAI-compatible, and Ollama
adapters; bounded model/tool loops; project-scoped tools; sequential role-based
workflows; cost accounting; contracts; audit and delivery records; and a
fail-closed Flutter verification gate.

Task execution follows `INTAKE → CLASSIFY → PLAN → EXECUTE → VERIFY → REVIEW →
DELIVER`. Typed records preserve risk, permissions, budgets, plan dependencies,
verification requirements, transition outcomes, and evidence references.

## Development

```bash
python3 -m venv .venv
. .venv/bin/activate
python -m pip install -e '.[dev]'
pytest
python -m flutter_agent.cli doctor
```

Tests also run from a checkout without an editable install:

```bash
python3 -m pytest
```

## CLI behavior

`doctor` is read-only. It detects a Flutter project and reports configuration,
architecture, dependency, and provider preflight findings.

`run` can modify files inside the selected project root. A model's completion
message is execution output, not verification evidence. For code-changing
Flutter tasks, the CLI selects and executes these mandatory checks:

```text
dart format --output=none --set-exit-if-changed .
flutter analyze
flutter test
```

An Android debug APK build is added when the task or changed scope is Android
specific and the project contains an Android target. A missing executable or a
timed-out command is `UNVERIFIED`; a non-zero exit is `FAILED`. Only successful
mandatory checks and acceptance-contract validation can produce `VERIFIED`.
Evidence is tied to a SHA-256 snapshot of the final project source, so later
changes invalidate the report.

Structured reports are written below `.flutter-agent/reports/`, and redacted
audit events below `.flutter-agent/audit/`. Neither a report nor an audit event
authorizes a commit, merge, release, or deployment.

Built-in playbooks cover investigation, bug fixes, features, refactoring, code
review, Flutter quality, and release readiness. Routing records the selected
playbook and rationale. Model IDs may be configured per role through
`agent.role_models` in `.flutter-agent/config.toml`.

The bounded repair loop receives failed checks, acceptance criteria, changed
files, and a source snapshot; it re-runs affected checks and stops repeated
failures without new evidence. Run the deterministic governance benchmark with:

```bash
PYTHONPATH=src python3 -m flutter_agent.benchmarks.runner
```

Its scope and limitations are documented in [benchmarks](docs/benchmarks.md).

See [the engineering audit](docs/engineering-audit.md) for confirmed defects,
implemented remediation, remaining limitations, and the next milestone.
