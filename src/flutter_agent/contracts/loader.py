from pathlib import Path
import tomllib

from flutter_agent.contracts.model import TaskContract


def load_contract(path: Path) -> TaskContract:
    data = tomllib.loads(path.read_text(encoding="utf-8"))
    return TaskContract(
        required_files=tuple(data.get("required_files", [])),
        required_symbols=tuple(data.get("required_symbols", [])),
        forbidden_content=tuple(data.get("forbidden_content", [])),
    )

