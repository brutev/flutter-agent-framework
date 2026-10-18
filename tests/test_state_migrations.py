import json

import pytest

from flutter_agent.state.migrations import StateMigrationError, ensure_state


def test_state_manifest_is_created(tmp_path):
    manifest = ensure_state(tmp_path)
    assert manifest.version == 1
    assert json.loads((tmp_path / ".flutter-agent" / "state.json").read_text())["version"] == 1


def test_future_state_version_is_rejected(tmp_path):
    directory = tmp_path / ".flutter-agent"
    directory.mkdir()
    (directory / "state.json").write_text('{"version": 999}')
    with pytest.raises(StateMigrationError, match="newer"):
        ensure_state(tmp_path)
