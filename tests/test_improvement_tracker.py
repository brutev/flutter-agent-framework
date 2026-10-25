from flutter_agent.improvement import FailureTracker


def test_tracker_requires_repeated_evidence_before_proposal() -> None:
    tracker = FailureTracker()
    tracker.record("formatting")
    assert tracker.proposals() == ()
    tracker.record("formatting")
    proposal = tracker.proposals()[0]
    assert proposal.occurrences == 2
    assert "deterministic formatting" in proposal.recommendation
