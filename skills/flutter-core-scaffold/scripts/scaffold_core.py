#!/usr/bin/env python3
"""Create a dependency-light Flutter lib/core scaffold without overwrites."""

from __future__ import annotations

import argparse
from pathlib import Path
import sys


FILES = {
    "lib/core/core.dart": """export 'config/app_config.dart';
export 'constants/app_constants.dart';
export 'errors/app_exception.dart';
export 'errors/failure.dart';
export 'interfaces/disposable.dart';
export 'navigation/app_navigator.dart';
export 'network/api_client.dart';
export 'services/app_logger.dart';
export 'storage/key_value_storage.dart';
export 'theme/app_theme.dart';
export 'usecase/use_case.dart';
export 'utils/result.dart';
""",
    "lib/core/config/app_config.dart": """final class AppConfig {
  const AppConfig({required this.environment, required this.isDebug});

  final String environment;
  final bool isDebug;
}
""",
    "lib/core/constants/app_constants.dart": """abstract final class AppConstants {
  static const Duration defaultTimeout = Duration(seconds: 30);
}
""",
    "lib/core/errors/app_exception.dart": """class AppException implements Exception {
  const AppException(this.message, {this.cause, this.stackTrace});

  final String message;
  final Object? cause;
  final StackTrace? stackTrace;

  @override
  String toString() => 'AppException: $message';
}
""",
    "lib/core/errors/failure.dart": """sealed class Failure {
  const Failure(this.message, {this.cause});

  final String message;
  final Object? cause;
}

final class UnexpectedFailure extends Failure {
  const UnexpectedFailure(super.message, {super.cause});
}
""",
    "lib/core/interfaces/disposable.dart": """abstract interface class Disposable {
  Future<void> dispose();
}
""",
    "lib/core/navigation/app_navigator.dart": """abstract interface class AppNavigator {
  Future<T?> pushNamed<T extends Object?>(
    String routeName, {
    Object? arguments,
  });

  void pop<T extends Object?>([T? result]);
}
""",
    "lib/core/network/api_client.dart": """abstract interface class ApiClient {
  Future<Object?> get(Uri uri, {Map<String, String> headers = const {}});

  Future<Object?> post(
    Uri uri, {
    Object? body,
    Map<String, String> headers = const {},
  });
}
""",
    "lib/core/services/app_logger.dart": """import 'dart:developer' as developer;

abstract interface class AppLogger {
  void debug(String message);
  void error(String message, {Object? error, StackTrace? stackTrace});
}

final class DeveloperAppLogger implements AppLogger {
  const DeveloperAppLogger();

  @override
  void debug(String message) {
    developer.log(message, name: 'app');
  }

  @override
  void error(String message, {Object? error, StackTrace? stackTrace}) {
    developer.log(
      message,
      name: 'app',
      error: error,
      stackTrace: stackTrace,
      level: 1000,
    );
  }
}
""",
    "lib/core/storage/key_value_storage.dart": """abstract interface class KeyValueStorage {
  Future<void> write<T extends Object>(String key, T value);
  T? read<T extends Object>(String key);
  Future<void> remove(String key);
  Future<void> clear();
}
""",
    "lib/core/theme/app_theme.dart": """import 'package:flutter/material.dart';

abstract final class AppTheme {
  static ThemeData light() =>
      ThemeData(brightness: Brightness.light, useMaterial3: true);

  static ThemeData dark() =>
      ThemeData(brightness: Brightness.dark, useMaterial3: true);
}
""",
    "lib/core/usecase/use_case.dart": """abstract interface class UseCase<Output, Input> {
  Future<Output> call(Input input);
}

final class NoInput {
  const NoInput();
}
""",
    "lib/core/utils/result.dart": """sealed class Result<T> {
  const Result();

  R fold<R>({
    required R Function(T value) onSuccess,
    required R Function(Object error) onFailure,
  });
}

final class Success<T> extends Result<T> {
  const Success(this.value);

  final T value;

  @override
  R fold<R>({
    required R Function(T value) onSuccess,
    required R Function(Object error) onFailure,
  }) =>
      onSuccess(value);
}

final class Error<T> extends Result<T> {
  const Error(this.error);

  final Object error;

  @override
  R fold<R>({
    required R Function(T value) onSuccess,
    required R Function(Object error) onFailure,
  }) =>
      onFailure(error);
}
""",
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project", type=Path, required=True)
    parser.add_argument("--dry-run", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    root = args.project.expanduser().resolve()
    if not root.is_dir() or not (root / "pubspec.yaml").is_file():
        print(f"error: not a Flutter project root: {root}", file=sys.stderr)
        return 2
    if not (root / "lib").is_dir():
        print(f"error: missing lib directory: {root / 'lib'}", file=sys.stderr)
        return 2

    created = 0
    skipped = 0
    for relative, content in FILES.items():
        target = (root / relative).resolve(strict=False)
        try:
            target.relative_to(root)
        except ValueError:
            print(f"error: target escapes project root: {relative}", file=sys.stderr)
            return 2
        if target.exists():
            print(f"SKIP   {relative}")
            skipped += 1
            continue
        print(f"{'PLAN' if args.dry_run else 'CREATE'} {relative}")
        if not args.dry_run:
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(content, encoding="utf-8")
        created += 1

    action = "planned" if args.dry_run else "created"
    print(f"{action}={created} skipped={skipped}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
