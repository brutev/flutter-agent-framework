from pathlib import Path

from flutter_agent.contracts.model import TaskContract
from flutter_agent.contracts.validator import validate_contract


def test_contract_passes_required_file_and_symbol(tmp_path: Path) -> None:
    file = tmp_path / "lib" / "login.dart"
    file.parent.mkdir()
    file.write_text("class LoginCubit {}", encoding="utf-8")
    contract = TaskContract(required_files=("lib/login.dart",), required_symbols=("LoginCubit",))
    result = validate_contract(tmp_path, contract)
    assert result.passed


def test_contract_reports_missing_file_and_forbidden_content(tmp_path: Path) -> None:
    file = tmp_path / "lib" / "login.dart"
    file.parent.mkdir()
    file.write_text("import 'package:flutter/material.dart';", encoding="utf-8")
    contract = TaskContract(
        required_files=("lib/login.dart", "lib/login_test.dart"),
        forbidden_content=("package:flutter/material.dart",),
    )
    result = validate_contract(tmp_path, contract)
    assert not result.passed
    assert any("missing" in finding.lower() for finding in result.findings)
    assert any("forbidden" in finding.lower() for finding in result.findings)

