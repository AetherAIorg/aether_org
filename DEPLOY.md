# Deploy

Production deployment is handled by the **[deployments](https://github.com/AetherAIorg/deployments)** repo.

## Flow

1. Merge to `main` in this repo
2. [`trigger-deploy.yml`](.github/workflows/trigger-deploy.yml) sends `repository_dispatch` to deployments
3. Deployments bumps the `app/` submodule and redeploys the DigitalOcean backend, Vercel, and GitHub Pages

## Setup (one time)

See the deployments repo [README](https://github.com/AetherAIorg/deployments/blob/main/README.md):

- DigitalOcean droplet + [`do/docker-compose.prod.yml`](https://github.com/AetherAIorg/deployments/blob/main/do/docker-compose.prod.yml)
- Vercel project for `metricgraph/frontend`
- Neo4j Aura + Cloudflare R2 in droplet `do/.env`
- GitHub secrets: `DEPLOYMENTS_DISPATCH_TOKEN` here, `DO_*` and Vercel secrets in deployments

## Local development

See [DOCKER.md](DOCKER.md) — `docker compose up -d --build` at repo root.

## PyPI (margin SDK)

Tag `margin-v*` to publish via [`.github/workflows/publish-pypi.yml`](.github/workflows/publish-pypi.yml).
