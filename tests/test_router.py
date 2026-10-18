from flutter_agent.routing.router import route_task


def test_router_uses_free_model_for_read_only_task() -> None:
    decision = route_task("List the dependencies from pubspec.yaml")
    assert decision.category == "read_only"
    assert decision.models[0].endswith(":free")


def test_router_uses_deepseek_for_edits() -> None:
    decision = route_task("Add a Cubit and update the login files")
    assert decision.category == "implementation"
    assert decision.models[0] == "deepseek/deepseek-v4.1-flash-1017"

