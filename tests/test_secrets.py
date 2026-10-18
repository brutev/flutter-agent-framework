from flutter_agent.security.secrets import redact_secrets


def test_redacts_known_secret_and_bearer_values():
    text = "Authorization: Bearer sk-secret api_key=other-secret"
    assert "sk-secret" not in redact_secrets(text, ["sk-secret"])
    assert "other-secret" not in redact_secrets(text)
    assert "[REDACTED]" in redact_secrets(text)
