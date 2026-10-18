from pathlib import Path


class ScopeViolation(PermissionError):
    """Raised when an operation leaves the approved project root."""


class ProjectScope:
    def __init__(self, root: Path):
        self.root = root.expanduser().resolve()
        if not self.root.is_dir():
            raise ValueError(f"Project root is not a directory: {self.root}")

    def resolve(self, relative_path: str | Path = ".") -> Path:
        candidate = Path(relative_path)
        if candidate.is_absolute():
            target = candidate.expanduser().resolve(strict=False)
        else:
            target = (self.root / candidate).resolve(strict=False)
        try:
            target.relative_to(self.root)
        except ValueError as exc:
            raise ScopeViolation(f"Path is outside the project root: {relative_path}") from exc
        return target

