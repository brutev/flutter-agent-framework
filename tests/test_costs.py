from flutter_agent.costs.ledger import CostLedger


def test_cost_ledger_records_usage_and_budget() -> None:
    ledger = CostLedger(budget_usd=1.0, input_per_million=1.0, output_per_million=2.0)
    record = ledger.record(500_000, 250_000)
    assert record.cost_usd == 1.0
    assert ledger.spent_usd == 1.0
    assert ledger.exceeded


def test_cost_ledger_can_reserve_output() -> None:
    ledger = CostLedger(budget_usd=1.0, input_per_million=1.0, output_per_million=2.0)
    assert ledger.can_reserve(500_000, 250_000)
    assert not ledger.can_reserve(1_000_000, 1_000_000)


def test_zero_budget_allows_zero_cost_free_calls() -> None:
    ledger = CostLedger(budget_usd=0.0, input_per_million=0.0, output_per_million=0.0)
    ledger.record(100_000, 100_000)
    assert not ledger.exceeded

