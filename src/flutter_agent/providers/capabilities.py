from dataclasses import dataclass


@dataclass(frozen=True)
class ModelSpec:
    model: str
    supports_tools: bool = True
    supports_structured_output: bool = False
    input_per_million: float = 0.1
    output_per_million: float = 0.5


class ModelCatalog:
    def __init__(self, models: list[ModelSpec] | tuple[ModelSpec, ...] = ()):
        self._models = {model.model: model for model in models}

    def require(self, model: str, tools: bool = False, structured_output: bool = False) -> ModelSpec:
        spec = self._models.get(model)
        if spec is None:
            raise ValueError(f"Unknown model capability profile: {model}")
        if tools and not spec.supports_tools:
            raise ValueError(f"Model does not support tool calling: {model}")
        if structured_output and not spec.supports_structured_output:
            raise ValueError(f"Model does not support structured output: {model}")
        return spec

