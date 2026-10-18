from dataclasses import dataclass
from pathlib import Path
import re


@dataclass(frozen=True)
class ProjectProfile:
    architecture: str
    state_management: str
    http_client: str
    routing: str
    dependency_injection: str
    dependencies: tuple[str, ...]


def detect_profile(root: Path) -> ProjectProfile:
    root = root.expanduser().resolve()
    pubspec = root / "pubspec.yaml"
    text = pubspec.read_text(encoding="utf-8") if pubspec.exists() else ""
    dependencies = tuple(sorted(set(re.findall(r"^\s{2}([a-zA-Z0-9_]+):", text, re.MULTILINE))))
    has_clean_layers = (root / "lib" / "domain").is_dir() and (root / "lib" / "data").is_dir()
    return ProjectProfile(
        architecture="clean_architecture" if has_clean_layers else "unknown",
        state_management="cubit_or_bloc" if "flutter_bloc" in dependencies else "unknown",
        http_client="dio" if "dio" in dependencies else "unknown",
        routing="go_router" if "go_router" in dependencies else "unknown",
        dependency_injection="get_it" if "get_it" in dependencies else "unknown",
        dependencies=dependencies,
    )

