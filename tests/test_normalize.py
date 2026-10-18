from flutter_agent.providers.normalize import normalize_openai, normalize_ollama


def test_normalizes_openai_content_and_tool_arguments():
    response = normalize_openai({"choices": [{"message": {"content": [{"text": "hi"}], "tool_calls": [{"function": {"name": "read_file", "arguments": "{\"path\":\"a.dart\"}"}}]}}]})
    assert response.text == "hi"
    assert response.tool_calls[0].arguments == {"path": "a.dart"}


def test_normalizes_ollama_response():
    response = normalize_ollama({"message": {"content": "ok"}, "prompt_eval_count": 2, "eval_count": 3})
    assert response.text == "ok"
    assert (response.input_tokens, response.output_tokens) == (2, 3)
