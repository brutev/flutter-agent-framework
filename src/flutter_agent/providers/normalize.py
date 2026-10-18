import json
from typing import Any

from flutter_agent.providers.base import ModelResponse, ToolCall


def _text(value: Any) -> str | None:
    if value is None or isinstance(value, str):
        return value
    if isinstance(value, list):
        parts = [part.get("text", "") for part in value if isinstance(part, dict)]
        return "".join(parts) or None
    return str(value)


def normalize_openai(data: dict[str, Any]) -> ModelResponse:
    choices = data.get("choices")
    if not isinstance(choices, list) or not choices:
        raise RuntimeError("Provider response did not contain choices")
    message = choices[0].get("message", {})
    if not isinstance(message, dict):
        raise RuntimeError("Provider response contained an invalid message")
    calls: list[ToolCall] = []
    for index, item in enumerate(message.get("tool_calls", [])):
        function = item.get("function", {})
        arguments = function.get("arguments", {})
        if isinstance(arguments, str):
            arguments = json.loads(arguments)
        if not isinstance(arguments, dict):
            raise ValueError("Provider returned non-object tool arguments")
        calls.append(ToolCall(item.get("id", f"tool-call-{index}"), function["name"], arguments))
    usage = data.get("usage", {})
    return ModelResponse(_text(message.get("content")), tuple(calls), usage.get("prompt_tokens", 0), usage.get("completion_tokens", 0))


def normalize_ollama(data: dict[str, Any]) -> ModelResponse:
    message = data.get("message", {})
    if not isinstance(message, dict):
        raise RuntimeError("Ollama response contained an invalid message")
    calls = tuple(
        ToolCall(f"ollama-call-{index}", item["function"]["name"], item["function"].get("arguments", {}))
        for index, item in enumerate(message.get("tool_calls", []))
    )
    return ModelResponse(_text(message.get("content")), calls, data.get("prompt_eval_count", 0), data.get("eval_count", 0))
