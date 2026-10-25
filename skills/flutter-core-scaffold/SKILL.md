---
name: flutter-core-scaffold
description: Create or extend a Flutter project's lib/core foundation with safe starter folders, class files, and dependency-light generic implementations. Use when the user asks to create, scaffold, initialize, or plan a Core folder; do not use for feature folders or for replacing an established core architecture.
---

# Flutter Core Scaffold

Create a minimal, compilable `lib/core` foundation that matches the target project instead of copying a project-specific Core implementation.

## Workflow

1. Locate the Flutter project by finding `pubspec.yaml`; read repository instructions and inspect `pubspec.yaml`, `analysis_options.yaml`, `lib/`, and existing `lib/core` files.
2. If `lib/core` already has an architecture, extend its conventions. Never replace or reorganize it without an explicit request.
3. Show the intended manifest briefly. Use `scripts/scaffold_core.py --project <root> --dry-run` for the default manifest.
4. Create only missing files. Never overwrite a non-empty existing file.
5. Fully implement dependency-free primitives: failures, exceptions, results, disposable contracts, use-case contracts, and safe logging.
6. For project-specific concerns—API libraries, navigation, storage backends, environment values, analytics, theme tokens, and dependency injection—create typed interfaces or small extension points, not invented production behavior.
7. Keep dependency direction inward: `core` must not import from `features`. Never add secrets, endpoints, business identifiers, or feature widgets.
8. Format created Dart files and run scoped analysis. If checks cannot run, report them as blocked rather than claiming verification.
9. Report created, skipped, and deferred files with actual command results.

## Default commands

```bash
python3 <skill-dir>/scripts/scaffold_core.py --project <flutter-project-root> --dry-run
python3 <skill-dir>/scripts/scaffold_core.py --project <flutter-project-root>
dart format lib/core
flutter analyze lib/core
```

Use `--dry-run` unless the user has already clearly authorized creation. The script validates the Flutter root, rejects paths outside it, and skips every existing target.

## Boundaries

- Do not add packages unless the user requests a concrete integration.
- Do not create service locators, repository hierarchies, or factories without demonstrated consumers.
- Do not put feature UI, domain rules, credentials, or environment secrets in Core.
- Do not generate barrel exports for nonexistent files.
- Scoped analysis does not prove the full application builds; report only actual evidence.
