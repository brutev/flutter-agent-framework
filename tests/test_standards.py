from flutter_agent.skills.catalog import Skill, SkillCatalog
from flutter_agent.standards.rules import RuleSet, validate_dart_source


def test_domain_forbidden_import_is_reported() -> None:
    rules = RuleSet(domain_forbidden_imports=("flutter", "dio"))
    findings = validate_dart_source("lib/domain/entities/user.dart", "import 'package:flutter/material.dart';", rules)
    assert any("forbidden" in finding.message.lower() for finding in findings)


def test_cubit_file_naming_is_reported() -> None:
    rules = RuleSet(cubit_filename_pattern=r"^[a-z][a-z0-9_]*_cubit\.dart$")
    findings = validate_dart_source("lib/presentation/cubit/LoginCubit.dart", "class LoginCubit {}", rules)
    assert any("naming" in finding.message.lower() for finding in findings)


def test_skill_catalog_selects_matching_skill() -> None:
    catalog = SkillCatalog([
        Skill("cubit", "Create Cubit states and tests", ("cubit", "state management")),
        Skill("api", "Integrate an API", ("api", "endpoint")),
    ])
    selected = catalog.select("Add a Cubit for the login feature")
    assert [skill.name for skill in selected] == ["cubit"]

