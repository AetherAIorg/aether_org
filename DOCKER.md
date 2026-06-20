# Docker — full stack

Runs everything in this repo **except** `prev/`.

## Quick start

```bash
cp .env.example .env   # optional: add OPENROUTER_API_KEY, connector tokens

docker compose up -d --build
```

## Ports

| Service | URL |
|---------|-----|
| MetricGraph API | http://localhost:8000 |
| MetricGraph UI | http://localhost:3000 |
| Margin Catalog API | http://localhost:8090 |
| Margin Catalog UI | http://localhost:3001 |
| Integration Hub | http://localhost:8080 |
| Neo4j Browser | http://localhost:7474 |
| MinIO Console | http://localhost:9001 |
| Marketing pages | http://localhost:4000 |

## API keys

Mint workspace keys after the stack is up:

```bash
docker compose run --rm mg-api python -m app.cli workspaces create --name "Default"
docker compose run --rm mg-api python -m app.cli keys create --workspace default --role ingest
docker compose run --rm mg-api python -m app.cli keys create --workspace default --role read
```

Add the ingest key to root `.env` as `INGEST_API_KEY=...` and the read key as `MARGIN_API_KEY=...`, then:

```bash
docker compose up -d ingest-engine hub catalog-api
```

## Individual projects

Subdirectories still have their own `docker-compose.yml` for running services in isolation during development.

## Logs

```bash
docker compose logs -f mg-api hub ingest-engine
```
