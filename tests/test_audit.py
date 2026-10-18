import json

from flutter_agent.reporting.audit import AuditLog


def test_audit_log_is_jsonl_and_redacts_secrets(tmp_path):
    audit = AuditLog(tmp_path)
    audit.record("run_started", token="Bearer sk-secret")
    event = json.loads((tmp_path / ".flutter-agent" / "audit" / "events.jsonl").read_text())
    assert event["event"] == "run_started"
    assert "sk-secret" not in json.dumps(event)
