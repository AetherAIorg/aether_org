from __future__ import annotations

import hmac
import json
import logging
from contextlib import asynccontextmanager
from urllib.parse import parse_qs

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from app import formatting
from app.agent.context_agent import ContextAgent
from app.clients.activity_client import ActivityClient
from app.clients.margin_client import MarginClient
from app.config import Settings, settings as default_settings
from app.connectors.linear import LinearConnector
from app.connectors.slack import SlackConnector
from app.connectors.teams import TeamsConnector
from app.events import Event
from app.metricgraph_client import MetricGraphClient
from app.query_router import parse_query
from app.router import Router
from app.routing_config import MarginConfig, RoutingConfig, load_margin_config, load_routing
from app.state import StateStore

logger = logging.getLogger(__name__)


class Hub:
    """Container wiring connectors, state, the MetricGraph client, and router."""

    def __init__(self, settings: Settings, routing: RoutingConfig | None = None) -> None:
        self.settings = settings
        self.state = StateStore(settings.state_db)
        self.mg = MetricGraphClient(settings.metricgraph_base_url)
        self.margin_config = load_margin_config(settings.hub_config_file)
        api_key = settings.margin_api_key or self.margin_config.default_api_key
        self.margin = MarginClient(self.margin_config.base_url or settings.metricgraph_base_url, api_key)
        self.context_agent = ContextAgent(self.margin, openrouter_api_key=settings.openrouter_api_key)
        self.slack = SlackConnector(
            bot_token=settings.slack_bot_token,
            signing_secret=settings.slack_signing_secret,
            alert_channel=settings.slack_alert_channel,
            info_channel=settings.slack_info_channel,
            ingest_channel=settings.slack_ingest_channel,
        )
        self.teams = TeamsConnector(
            incoming_webhook_url=settings.teams_incoming_webhook_url,
            outgoing_webhook_secret=settings.teams_outgoing_webhook_secret,
        )
        self.linear = LinearConnector(
            api_key=settings.linear_api_key,
            webhook_secret=settings.linear_webhook_secret,
            team_id=settings.linear_team_id,
            bot_user_id=settings.linear_bot_user_id,
        )
        self.routing = routing or load_routing(settings.hub_config_file)
        self.router = Router(self.slack, self.teams, self.linear, self.state, self.routing)

    def verify_hub_secret(self, provided: str | None) -> bool:
        secret = self.settings.hub_webhook_secret
        if not secret:
            logger.warning("HUB_WEBHOOK_SECRET not set; accepting inbound event without auth")
            return True
        return bool(provided) and hmac.compare_digest(secret, provided)

    def close(self) -> None:
        self.state.close()
        self.mg.close()
        self.margin.close()
        self.slack.close()
        self.teams.close()
        self.linear.close()

    def margin_client_for_team(self, team_id: str | None) -> MarginClient:
        key = self.margin_config.api_key_for_team(team_id) or self.settings.margin_api_key
        if not key:
            return self.margin
        if key == self.margin.api_key:
            return self.margin
        return MarginClient(self.margin_config.base_url or self.settings.metricgraph_base_url, key)

    def context_agent_for_team(self, team_id: str | None) -> ContextAgent:
        client = self.margin_client_for_team(team_id)
        return ContextAgent(client, openrouter_api_key=self.settings.openrouter_api_key)


def create_app(hub: Hub | None = None) -> FastAPI:
    @asynccontextmanager
    async def lifespan(app: FastAPI):
        if getattr(app.state, "hub", None) is None:
            app.state.hub = Hub(default_settings)
        yield
        app.state.hub.close()

    app = FastAPI(title="Integration Hub", lifespan=lifespan)
    if hub is not None:
        app.state.hub = hub
    else:
        app.state.hub = None

    def get_hub() -> Hub:
        return app.state.hub

    @app.get("/health")
    def health():
        return {"status": "ok"}

    # --- Inbound events from MetricGraph and ingest_engine ---

    async def _handle_event(request: Request) -> JSONResponse:
        hub = get_hub()
        raw = await request.body()
        if not hub.verify_hub_secret(request.headers.get("x-hub-secret")):
            return JSONResponse({"error": "invalid secret"}, status_code=401)
        try:
            event = Event.model_validate_json(raw)
        except Exception as exc:  # noqa: BLE001
            return JSONResponse({"error": f"invalid event: {exc}"}, status_code=400)
        result = hub.router.dispatch(event)
        return JSONResponse(result)

    @app.post("/webhooks/metricgraph")
    async def metricgraph_webhook(request: Request):
        return await _handle_event(request)

    @app.post("/webhooks/ingest")
    async def ingest_webhook(request: Request):
        return await _handle_event(request)

    # --- Inbound Slack ---

    @app.post("/slack/commands")
    async def slack_commands(request: Request):
        hub = get_hub()
        raw = await request.body()
        if not hub.slack.verify_signature(_lower_headers(request.headers), raw):
            return JSONResponse({"error": "bad signature"}, status_code=401)
        form = {k: v[0] for k, v in parse_qs(raw.decode("utf-8")).items()}
        text = (form.get("text") or "").strip()
        return JSONResponse(_handle_slack_command(hub, text))

    @app.post("/slack/interactions")
    async def slack_interactions(request: Request):
        hub = get_hub()
        raw = await request.body()
        if not hub.slack.verify_signature(_lower_headers(request.headers), raw):
            return JSONResponse({"error": "bad signature"}, status_code=401)
        form = {k: v[0] for k, v in parse_qs(raw.decode("utf-8")).items()}
        payload = json.loads(form.get("payload", "{}"))
        return JSONResponse(_handle_slack_interaction(hub, payload))

    # --- Inbound Teams (Outgoing Webhook) ---

    @app.post("/teams/messages")
    async def teams_messages(request: Request):
        hub = get_hub()
        raw = await request.body()
        if not hub.teams.verify_signature(request.headers.get("authorization", ""), raw):
            return JSONResponse({"error": "bad signature"}, status_code=401)
        body = json.loads(raw.decode("utf-8") or "{}")
        text = (body.get("text") or "").strip()
        # Teams prefixes the bot mention; strip a leading "metric" keyword group.
        return JSONResponse(_handle_teams_message(hub, text))

    # --- Inbound Linear ---

    @app.post("/webhooks/linear")
    async def linear_webhook(request: Request):
        hub = get_hub()
        raw = await request.body()
        signature = request.headers.get("linear-signature", "")
        if not hub.linear.verify_signature(signature, raw):
            return JSONResponse({"error": "bad signature"}, status_code=401)
        body = json.loads(raw.decode("utf-8") or "{}")
        return JSONResponse(_handle_linear_event(hub, body))

    return app


def _lower_headers(headers) -> dict[str, str]:
    return {k.lower(): v for k, v in headers.items()}


# --- Slack handlers ---

def _handle_slack_command(hub: Hub, text: str) -> dict:
    parts = text.split(maxsplit=1)
    verb = parts[0].lower() if parts else ""
    rest = parts[1].strip() if len(parts) > 1 else ""

    if verb == "search" and rest:
        results = hub.mg.search(rest)
        return {"response_type": "ephemeral", "blocks": formatting.slack_blocks_for_search(rest, results)}
    if verb == "issues":
        issues = hub.mg.list_issues()
        if not issues:
            return {"response_type": "ephemeral", "text": "No open issues."}
        lines = [f"*{i.get('title')}* ({i.get('issue_type')}, sev {i.get('severity')})" for i in issues[:10]]
        return {"response_type": "ephemeral", "text": "\n".join(lines)}
    if verb == "approve" and rest:
        try:
            metric = hub.mg.approve_metric(rest, approved_by="slack")
            return {"response_type": "in_channel", "text": f"Approved *{metric.get('canonical_name')}*."}
        except Exception as exc:  # noqa: BLE001
            return {"response_type": "ephemeral", "text": f"Approve failed: {exc}"}

    # Default: treat the whole text as a metric definition lookup.
    query = text or ""
    if not query:
        return {"response_type": "ephemeral", "text": "Usage: `/metric <name>`, `/metric search <q>`, `/metric issues`, `/metric approve <id>`"}
    metric = hub.mg.find_metric_by_name(query)
    if not metric:
        return {"response_type": "ephemeral", "text": formatting.metric_not_found_markdown(query)}
    return {"response_type": "ephemeral", "blocks": formatting.slack_blocks_for_metric(metric)}


def _handle_slack_interaction(hub: Hub, payload: dict) -> dict:
    actions = payload.get("actions") or []
    if not actions:
        return {"text": "No action."}
    action = actions[0]
    action_id = action.get("action_id", "")
    value = action.get("value", "")
    if action_id == "approve_metric" and value:
        try:
            metric = hub.mg.approve_metric(value, approved_by="slack")
            return {"text": f"Approved *{metric.get('canonical_name')}*."}
        except Exception as exc:  # noqa: BLE001
            return {"text": f"Approve failed: {exc}"}
    return {"text": f"Unhandled action: {action_id}"}


# --- Teams handler ---

def _log_activity(hub: Hub, client: MarginClient, channel: str, intent: str, query: str, answer: str, **extra) -> None:
    activity = ActivityClient(client.base_url, client.api_key)
    try:
        metric_id = None
        if intent != "search":
            metric = client.find_metric_by_name(query)
            metric_id = metric.get("id") if metric else None
        activity.log_query(
            {
                "channel": channel,
                "intent": intent,
                "query_text": query,
                "answer_preview": answer[:500],
                "answer_full": answer,
                "metric_id": metric_id,
                **extra,
            }
        )
    finally:
        activity.close()


def _handle_teams_message(hub: Hub, text: str) -> dict:
    parsed = parse_query(text) or _teams_fallback_parse(text)
    if not parsed:
        return formatting.teams_text_card(
            "Metric lookup", "Ask `metric: <name>` or `/metric search <query>`."
        )
    intent, query = parsed
    agent = hub.context_agent
    if intent == "search":
        answer = agent.answer(intent, query)
        _log_activity(hub, hub.margin, "teams", intent, query, answer)
        return formatting.teams_text_card(f"Search: {query}", answer)
    answer = agent.answer(intent, query)
    _log_activity(hub, hub.margin, "teams", intent, query, answer)
    return formatting.teams_text_card(query, answer)


def _teams_fallback_parse(text: str) -> tuple[str, str] | None:
    cleaned = (text or "").strip()
    if cleaned:
        return "definition", cleaned
    return None


# --- Linear handler ---

def _handle_linear_event(hub: Hub, body: dict) -> dict:
    comment = hub.linear.extract_comment(body)
    if not comment:
        return {"status": "ignored", "reason": "not a comment create"}
    # Avoid replying to our own comments (loop guard).
    if hub.settings.linear_bot_user_id and comment.get("author_id") == hub.settings.linear_bot_user_id:
        return {"status": "ignored", "reason": "self-authored"}
    comment_id = comment.get("comment_id")
    if comment_id and not hub.state.mark_comment(comment_id):
        return {"status": "duplicate", "comment_id": comment_id}

    parsed = hub.linear.parse_query(comment.get("text", ""))
    if not parsed:
        return {"status": "ignored", "reason": "no metric query"}
    intent, query = parsed
    team_id = (body.get("data") or {}).get("teamId") or hub.settings.linear_team_id
    margin_client = hub.margin_client_for_team(team_id)
    agent = ContextAgent(margin_client, openrouter_api_key=hub.settings.openrouter_api_key)
    answer = hub.linear.answer_query(agent, intent, query)
    issue = (body.get("data") or {}).get("issue") or {}
    _log_activity(
        hub,
        margin_client,
        "linear",
        intent,
        query,
        answer,
        external_ref=comment.get("comment_id"),
        external_url=issue.get("url"),
        author=comment.get("author_id"),
    )
    issue_id = comment.get("issue_id")
    if issue_id:
        hub.linear.create_comment(issue_id, answer, parent_id=comment.get("parent_id"))
    return {"status": "answered", "intent": intent, "query": query}


app = create_app()
