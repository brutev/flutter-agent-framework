from pathlib import Path

from flutter_agent.contracts.loader import load_contract


def test_load_contract_from_toml(tmp_path: Path) -> None:
    path = tmp_path / "login.toml"
    path.write_text(
        'required_files = ["lib/login.dart"]\n'
        'required_symbols = ["LoginCubit"]\n'
        'forbidden_content = ["print("]\n',
        encoding="utf-8",
    )
    contract = load_contract(path)
    assert contract.required_files == ("lib/login.dart",)
    assert contract.required_symbols == ("LoginCubit",)

