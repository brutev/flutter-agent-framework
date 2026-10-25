from flutter_agent.benchmarks.catalog import BENCHMARK_TASKS
from flutter_agent.benchmarks.runner import run_benchmarks


def test_benchmark_catalog_covers_ten_required_scenarios() -> None:
    assert len(BENCHMARK_TASKS) == 10
    assert len({task.id for task in BENCHMARK_TASKS}) == 10


def test_benchmarks_are_reproducible_and_match_expected_outcomes() -> None:
    results = run_benchmarks()
    assert len(results) == 10
    assert all(result.passed for result in results)
    assert all(result.evidence for result in results)
