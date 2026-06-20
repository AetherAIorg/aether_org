# Integration Hub

A Python + FastAPI bridge that connects **MetricGraph** and **ingest_engine** to
**Slack**, **Microsoft Teams**, and **Linear**.

It does two things:

1. **Outbound notifications** — MetricGraph and ingest_engine POST canonical
   events to the hub, which fans them out to Slack/Teams and auto-files deduped
   Linear issues for metric conflicts.
2. **Inbound questions** — ask about a metric from Slack, Teams, or **Linear**
   and the hub fetches the answer from the MetricGraph registry and replies in
   the same thread/issue.

## Architecture

```
ingest_engine ──file.*──┐
                        ├──► /webhooks/ingest ──┐
MetricGraph ──events────┴──► /webhooks/metricgraph │
                                                    ▼
                                          ┌───────────────────┐
                                          │   Router + State  │
                                          │ (sqlite dedupe)   │
                                          └───────┬───────────┘
                              ┌───────────────────┼───────────────────┐
                              ▼                   ▼                   ▼
                            Slack               Teams              Linear
                              │                   │                   │
        /slack/commands ◄─────┘   /teams/messages ┘   /webhooks/linear┘
                              └──────────► MetricGraph REST ◄──────────┘
                                   (search / registry / approve)
```

## Inbound event schema

Both MetricGraph and ingest_engine post this JSON (with an `X-Hub-Secret`
header) to `/webhooks/metricgraph` and `/webhooks/ingest`:

```json
{
  "source": "metricgraph",
  "event": "issue.detected",
  "id": "<idempotency-key>",
  "ts": "2026-06-15T22:00:00Z",
  "payload": { "issue_type": "CONFLICTING_DEFINITION", "title": "...", "severity": 4, "affected_artifacts": ["a.sql"] }
}
```

Event types: `issue.detected`, `parse.failed`, `metric.candidate.discovered`,
`metric.approved`, `metric.run.completed`, `file.added`, `file.modified`,
`file.removed`.

## Routing (defaults)

| Event | Slack | Teams | Linear issue |
|-------|-------|-------|--------------|
| `issue.detected` | alert channel | yes | yes (deduped) |
| `parse.failed` | alert channel | yes | no |
| `metric.candidate.discovered` | info channel | optional | no |
| `metric.approved` | info channel | optional | no |
| `metric.run.completed` | info channel | optional | no |
| `file.*` | ingest channel | optional | no |

Toggle behavior in `config.yaml` (see `config.example.yaml`).

## Inbound "ask about a metric"

- **Linear**: comment `metric: gross irr`, `/metric search net irr`, or
  `@MetricGraph what is Gross IRR?` on any issue. The hub looks it up in the
  registry and replies as a Linear comment.
- **Slack**: `/metric <name>`, `/metric search <q>`, `/metric issues`,
  `/metric approve <metric_id>`.
- **Teams**: send `metric: <name>` / `metric search <q>` to the bot (Outgoing
  Webhook).

## Setup

```bash
cd integration_hub
python3 -m venv .venv && .venv/bin/pip install -r requirements.txt
cp .env.example .env          # fill in tokens/secrets for the platforms you use
cp config.example.yaml config.yaml
.venv/bin/uvicorn app.main:app --port 8080
```

Everything is optional: connectors with no token configured simply log and
skip, so you can run with only the platforms you've set up.

### Wire the producers

MetricGraph (`metricgraph/.env`):

```
INTEGRATION_WEBHOOK_URL=http://localhost:8080/webhooks/metricgraph
INTEGRATION_WEBHOOK_SECRET=change-me
```

ingest_engine (`ingest_engine/config.yaml`):

```yaml
sink:
  type: composite          # feeds MetricGraph AND notifies the hub
  metricgraph:
    base_url: http://localhost:8000
  webhook:
    url: http://localhost:8080/webhooks/ingest
    secret: change-me
```

## Platform credentials

| Platform | Env vars | Notes |
|----------|----------|-------|
| Slack | `SLACK_BOT_TOKEN`, `SLACK_SIGNING_SECRET`, `SLACK_*_CHANNEL` | Bot token `chat:write`; point slash command + interactivity at `/slack/commands` and `/slack/interactions` |
| Teams | `TEAMS_INCOMING_WEBHOOK_URL`, `TEAMS_OUTGOING_WEBHOOK_SECRET` | Incoming Webhook for cards out; Outgoing Webhook (HMAC) -> `/teams/messages` |
| Linear | `LINEAR_API_KEY`, `LINEAR_WEBHOOK_SECRET`, `LINEAR_TEAM_ID`, `LINEAR_BOT_USER_ID` | Webhook (Comments) -> `/webhooks/linear` |

## Tests

```bash
.venv/bin/python -m pytest -q
```

## End-to-end

1. Start MetricGraph (`docker compose up` in `metricgraph/`) and seed the demo.
2. Start the hub (`uvicorn app.main:app --port 8080`).
3. Run ingest_engine with the `composite` sink against the demo folder.
4. Edit a demo `.sql` file -> ingest re-uploads to MetricGraph and the hub
   posts a `file.modified` message to Slack.
5. A conflicting metric definition -> Slack alert + a single Linear issue
   (re-runs do not duplicate it).
6. Comment `metric: gross irr` on that Linear issue -> the hub replies with the
   registry definition.
