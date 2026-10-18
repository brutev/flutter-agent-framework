# Flutter Agent Framework

Python framework for governed, provider-agnostic Flutter development. The
framework operates on Flutter projects, while its model provider is selected
through configuration. OpenRouter is the first adapter.

## Development

```bash
python3 -m venv .venv
. .venv/bin/activate
python -m pip install -e '.[dev]'
pytest
python -m flutter_agent.cli doctor
```

Phase 0 currently provides typed configuration, the provider abstraction, an
OpenRouter adapter, and a read-only CLI doctor. No project files are modified
by the agent yet.
