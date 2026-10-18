import pytest

from flutter_agent.providers.base import ModelResponse
from flutter_agent.providers.resilience import ResilientProvider


class Flaky:
    name = "flaky"

    def __init__(self):
        self.calls = 0

    def complete(self, messages, tools):
        self.calls += 1
        if self.calls < 2:
            raise RuntimeError("upstream 503")
        return ModelResponse("ok")


def test_resilience_retries_transient_failure():
    provider = Flaky()
    result = ResilientProvider(provider, retries=1, backoff_seconds=0).complete([], [])
    assert result.text == "ok"
    assert provider.calls == 2


def test_resilience_opens_circuit_after_repeated_failure():
    class Broken:
        name = "broken"

        def complete(self, messages, tools):
            raise RuntimeError("upstream 503")

    provider = ResilientProvider(Broken(), retries=0, failure_threshold=1, cooldown_seconds=60)
    with pytest.raises(RuntimeError, match="unavailable"):
        provider.complete([], [])
    with pytest.raises(RuntimeError, match="Circuit open"):
        provider.complete([], [])
