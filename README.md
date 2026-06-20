# aether_org

Margin monorepo — MetricGraph, integration hub, ingest engine, catalog, SDK, and marketing pages.

- **Local dev:** `docker compose up -d --build` (see [DOCKER.md](DOCKER.md))
- **Production deploy:** [AetherAIorg/deployments](https://github.com/AetherAIorg/deployments)

## Standalone mirrors

Components also sync to individual repos under [AetherAIorg](https://github.com/AetherAIorg):

| Component | Repo |
|-----------|------|
| Monorepo (all) | [aether_org](https://github.com/AetherAIorg/aether_org) |
| MetricGraph | [metricgraph](https://github.com/AetherAIorg/metricgraph) *(create repo, then run script)* |
| Integration hub | [integration_hub](https://github.com/AetherAIorg/integration_hub) |
| Ingest engine | [ingest_engine](https://github.com/AetherAIorg/ingest_engine) |
| Catalog | [registry_governance](https://github.com/AetherAIorg/registry_governance) *(create repo, then run script)* |
| SDK | [margin_sdk](https://github.com/AetherAIorg/margin_sdk) *(create repo, then run script)* |
| Marketing site | [margin_github_pages.github.io](https://github.com/AetherAIorg/margin_github_pages.github.io) |

Re-sync mirrors after monorepo changes:

```bash
./scripts/push-component-repos.sh
```

## Layout

| Directory | Description |
|-----------|-------------|
| `metricgraph/` | API, worker, frontend (auth, graph, activity) |
| `integration_hub/` | Slack / Teams / Linear bridge |
| `ingest_engine/` | File watcher → MetricGraph |
| `registry_governance/` | Margin Catalog API + UI |
| `margin_sdk/` | Python `margin` package |
| `margin_github_pages/` | Static landing site |
