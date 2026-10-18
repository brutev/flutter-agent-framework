from dataclasses import dataclass


@dataclass(frozen=True)
class UsageRecord:
    input_tokens: int
    output_tokens: int
    cost_usd: float


class CostLedger:
    def __init__(self, budget_usd: float, input_per_million: float = 0.10, output_per_million: float = 0.50):
        if budget_usd < 0 or input_per_million < 0 or output_per_million < 0:
            raise ValueError("Cost and budget values must be non-negative")
        self.budget_usd = budget_usd
        self.input_per_million = input_per_million
        self.output_per_million = output_per_million
        self.records: list[UsageRecord] = []

    @property
    def spent_usd(self) -> float:
        return sum(record.cost_usd for record in self.records)

    @property
    def exceeded(self) -> bool:
        # A zero budget is useful for free-tier-only runs.  Permit any number
        # of zero-cost calls, but stop as soon as a paid call records spend.
        if self.budget_usd == 0:
            return self.spent_usd > 0
        return self.spent_usd >= self.budget_usd

    def estimate(self, input_tokens: int, output_tokens: int) -> float:
        return (input_tokens / 1_000_000 * self.input_per_million) + (output_tokens / 1_000_000 * self.output_per_million)

    def can_reserve(self, input_tokens: int, output_tokens: int) -> bool:
        return self.spent_usd + self.estimate(input_tokens, output_tokens) <= self.budget_usd

    def record(self, input_tokens: int, output_tokens: int) -> UsageRecord:
        usage = UsageRecord(input_tokens, output_tokens, self.estimate(input_tokens, output_tokens))
        self.records.append(usage)
        return usage

