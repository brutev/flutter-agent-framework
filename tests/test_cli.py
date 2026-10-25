import json

from flutter_agent.cli import _save_report, doctor
from flutter_agent.reporting.report import DeliveryReport


def test_doctor_is_read_only(tmp_path, capsys) -> None:
    (tmp_path / "pubspec.yaml").write_text("name: example\n", encoding="utf-8")
    doctor(tmp_path)
    assert "Flutter project: detected" in capsys.readouterr().out
    assert not (tmp_path / ".flutter-agent").exists()


def test_delivery_report_redacts_secret_like_output(tmp_path) -> None:
    path = _save_report(
        tmp_path,
        DeliveryReport("inspect", False, outputs=("api_key=abcdefghijklmnop",)),
    )
    payload = json.loads(path.read_text(encoding="utf-8"))
    assert "abcdefghijklmnop" not in payload["outputs"][0]
    assert "[REDACTED]" in payload["outputs"][0]
