from flutter_agent.repair.controller import RepairController


def test_repair_stops_repeated_failure() -> None:
    calls = []

    def attempt(error: str) -> bool:
        calls.append(error)
        return False

    result = RepairController(max_attempts=3).run("analyzer failure", attempt)
    assert not result.repaired
    assert result.attempts == 1
    assert "repeated" in (result.error or "").lower()


def test_repair_succeeds_within_bound() -> None:
    calls = []

    def attempt(error: str) -> bool:
        calls.append(error)
        return (False, "different failure") if len(calls) == 1 else True

    result = RepairController(max_attempts=3).run("first failure", attempt)
    assert result.repaired
    assert result.attempts == 2

