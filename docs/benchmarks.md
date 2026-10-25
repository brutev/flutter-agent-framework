# Governance benchmarks

Run the deterministic benchmark suite with:

```bash
PYTHONPATH=src python3 -m flutter_agent.benchmarks.runner
```

The catalog contains the ten required scenarios: read-only exploration, Flutter
bug routing, Cubit quality routing, feature regression handling, formatting
failure, bounded repair, ambiguous acceptance criteria, project-root escape,
malformed provider response, and a false model success claim.

Each result records the audited baseline behavior, expected and actual outcome,
duration, estimated cost, repair count, human-intervention flag, and evidence.
CI stores the JSON result as an artifact for every supported Python version.

This is currently a deterministic governance-component benchmark. Its 100%
result proves the routing, status, verification, repair, and scope controls
behave as specified under fixtures. It does **not** measure end-to-end model
quality on real Flutter applications, so it must not be presented as the
framework's overall task success rate. Real-app fixtures, comparable provider
configurations, and repeated latency/cost samples remain future benchmark work.
