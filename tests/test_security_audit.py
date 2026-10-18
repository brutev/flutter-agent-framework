from flutter_agent.security.audit import scan_project


def test_security_scan_detects_secret(tmp_path):
    (tmp_path / "config.dart").write_text('const api_key = "sk-abcdefghijklmnopqrstuvwxyz";')
    findings = scan_project(tmp_path)
    assert findings[0].kind == "possible_secret"


def test_security_scan_detects_external_symlink(tmp_path):
    target = tmp_path.parent / "outside-secret.txt"
    target.write_text("secret")
    (tmp_path / "link.txt").symlink_to(target)
    findings = scan_project(tmp_path)
    assert any(item.kind == "symlink_escape" for item in findings)
