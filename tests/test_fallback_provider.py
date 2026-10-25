import pytest

from flutter_agent.providers.base import ModelResponse
from flutter_agent.providers.fallback import FallbackProvider
from flutter_agent.providers.errors import ProviderFailure, ProviderFailureCategory


class Failing:
    name = "failing"

    def complete(self, messages, tools):
        raise RuntimeError("provider failed")


class Working:
    name = "working"

    def complete(self, messages, tools):
        return ModelResponse("ok")


def test_fallback_provider_tries_next_provider() -> None:
    response = FallbackProvider((Failing(), Working())).complete([], [])
    assert response.text == "ok"


def test_fallback_provider_does_not_hide_permanent_failure() -> None:
    class Permanent:
        name = "permanent"

        def complete(self, messages, tools):
            raise ProviderFailure("bad credentials", ProviderFailureCategory.PERMANENT)

    with pytest.raises(ProviderFailure, match="credentials"):
        FallbackProvider((Permanent(), Working())).complete([], [])

