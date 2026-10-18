from flutter_agent.providers.capabilities import ModelCatalog, ModelSpec


def test_catalog_rejects_model_without_required_tools() -> None:
    catalog = ModelCatalog([
        ModelSpec("cheap", supports_tools=False, input_per_million=0.1, output_per_million=0.5),
        ModelSpec("agent", supports_tools=True, input_per_million=1, output_per_million=2),
    ])
    assert catalog.require("agent", tools=True).model == "agent"
    try:
        catalog.require("cheap", tools=True)
    except ValueError as exc:
        assert "tool" in str(exc).lower()
    else:
        raise AssertionError("incompatible model was accepted")

