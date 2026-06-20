# Deploy

Production deployment is handled by the **[deployments](https://github.com/AetherAIorg/deployments)** repo.

## Flow

1. Merge to `main` in this repo
2. [`trigger-deploy.yml`](.github/workflows/trigger-deploy.yml) sends `repository_dispatch` to deployments
3. Deployments bumps the `app/` submodule and redeploys Render, Vercel, and GitHub Pages

## Setup (one time)

See the deployments repo [README](https://github.com/AetherAIorg/deployments/blob/main/README.md):

- Render blueprint (`render.yaml`)
- Vercel projects for `metricgraph/frontend` and `registry_governance/frontend`
- Neo4j Aura + S3/R2 env on Render
- GitHub secrets: `DEPLOYMENTS_DISPATCH_TOKEN` here, platform secrets in deployments

## Local development

See [DOCKER.md](DOCKER.md) — `docker compose up -d --build` at repo root.

## PyPI (margin SDK)

Tag `margin-v*` to publish via [`.github/workflows/publish-pypi.yml`](.github/workflows/publish-pypi.yml).
