from dataclasses import dataclass


@dataclass(frozen=True)
class TaskContract:
    required_files: tuple[str, ...] = ()
    required_symbols: tuple[str, ...] = ()
    forbidden_content: tuple[str, ...] = ()

