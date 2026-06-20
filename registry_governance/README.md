# Margin Catalog — governance layer for the metric registry

Select Star–inspired **data governance** for teams and people on top of MetricGraph. Margin Catalog owns stewardship, documentation, certification, lineage views, and issue workflow — while MetricGraph remains the source of truth for tags, manifests, and execution.

## Architecture

```
MetricGraph (registry + discovery)
       │ REST sync + webhooks
       ▼
Margin Catalog (registry_governance)
       ├── People & Teams
       ├── Stewardship (owner / steward / expert)
       ├── Documentation & FAQs
       ├── Certification badges
       ├── Lineage graph
       └── Issue inbox (assign / status)
       ▼
Catalog UI (Next.js) — http://localhost:3001
```

## Quick start (dual stack)

**Terminal 1 — MetricGraph** (must be running first):

```bash
cd metricgraph
docker compose up --build
```

**Terminal 2 — Margin Catalog**:

```bash
cd registry_governance
cp .env.example .env
docker compose up --build
```

Services:
- **Catalog UI**: http://localhost:3001
- **Catalog API**: http://localhost:8090
- **API docs**: http://localhost:8090/docs
- **Registry UI** (MetricGraph): http://localhost:3000

On startup the catalog API syncs assets from MetricGraph and seeds demo teams/people if empty.

### Manual seed (after sync)

```bash
docker compose exec api python -m app.seed.run_seed
```

### Wire webhooks from MetricGraph

In `metricgraph/.env`:

```bash
GOVERNANCE_WEBHOOK_URL=http://host.docker.internal:8090/webhooks/metricgraph
GOVERNANCE_WEBHOOK_SECRET=your-shared-secret
```

Set the same secret in `registry_governance/.env` as `WEBHOOK_SECRET`.

### Registry cross-links

In `metricgraph/frontend`, set:

```bash
NEXT_PUBLIC_CATALOG_URL=http://localhost:3001
```

The registry sidebar shows **Margin Catalog** and metric pages link **View in Catalog**.

## Demo auth

Use header `X-Actor-Email` (e.g. `alex.chen@margin.local`) when creating annotations or setting certification. Demo users are created by the seed script.

## API highlights

| Method | Path | Purpose |
|--------|------|---------|
| GET | `/api/catalog` | Search assets with team/certification filters |
| GET | `/api/assets/{type}/{id}` | Asset hub payload |
| GET | `/api/lineage/{type}/{id}` | Lineage graph |
| GET/PATCH | `/api/issues` | Issue mirror with assignee/status |
| GET | `/api/teams/{id}/workspace` | Team dashboard |
| POST | `/api/sync/metricgraph` | Manual resync |
| POST | `/webhooks/metricgraph` | Incremental updates from registry |

## Tests

```bash
cd backend
pip install -r requirements.txt
pytest
```

## Project structure

```
registry_governance/
├── docker-compose.yml
├── backend/app/
│   ├── main.py
│   ├── models.py
│   ├── metricgraph_client.py
│   ├── sync/bootstrap.py
│   ├── lineage/builder.py
│   └── seed/run_seed.py
└── frontend/src/app/
    ├── page.tsx              # Catalog home
    ├── teams/
    ├── assets/[type]/[id]/   # Asset hub
    └── issues/
```

## Out of scope (MVP)

- SSO / Okta
- RBAC enforcement on MetricGraph publish/run
- Column-level warehouse lineage
- Replacing MetricGraph's issue detection engine
