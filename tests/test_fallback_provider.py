from flutter_agent.providers.base import ModelResponse
from flutter_agent.providers.fallback import FallbackProvider


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

