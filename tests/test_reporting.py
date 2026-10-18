from flutter_agent.reporting.report import DeliveryReport


def test_delivery_report_serializes_core_run_data() -> None:
    report = DeliveryReport(
        task="Add login",
        completed=True,
        stages=("analyst", "implementer"),
        outputs=("analysis", "implementation"),
    )
    data = report.to_dict()
    assert data["completed"] is True
    assert data["stages"] == ["analyst", "implementer"]
    assert "generated_at" in data

