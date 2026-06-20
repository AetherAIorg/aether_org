# aether_org

Margin monorepo — MetricGraph, integration hub, ingest engine, catalog, SDK, and marketing pages.

- **Local dev:** `docker compose up -d --build` (see [DOCKER.md](DOCKER.md))
- **Production deploy:** [AetherAIorg/deployments](https://github.com/AetherAIorg/deployments)

## Layout

| Directory | Description |
|-----------|-------------|
| `metricgraph/` | API, worker, frontend (auth, graph, activity) |
| `integration_hub/` | Slack / Teams / Linear bridge |
| `ingest_engine/` | File watcher → MetricGraph |
| `registry_governance/` | Margin Catalog API + UI |
| `margin_sdk/` | Python `margin` package |
| `margin_github_pages/` | Static landing site |
