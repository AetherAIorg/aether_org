from __future__ import annotations

from typing import Any

from app.events import (
    Event,
    FILE_ADDED,
    FILE_MODIFIED,
    FILE_REMOVED,
    ISSUE_DETECTED,
    METRIC_APPROVED,
    METRIC_CANDIDATE_DISCOVERED,
    METRIC_RUN_COMPLETED,
    PARSE_FAILED,
)

_EVENT_TITLES = {
    ISSUE_DETECTED: "Metric conflict detected",
    PARSE_FAILED: "Artifact parse failed",
    METRIC_CANDIDATE_DISCOVERED: "New metric candidate discovered",
    METRIC_APPROVED: "Metric approved",
    METRIC_RUN_COMPLETED: "Metric run completed",
    FILE_ADDED: "File added",
    FILE_MODIFIED: "File changed",
    FILE_REMOVED: "File removed",
}


def event_title(event: Event) -> str:
    return _EVENT_TITLES.get(event.event, event.event)


def event_summary(event: Event) -> str:
    """One-line human summary used as fallback text everywhere."""
    p = event.payload
    if event.event == ISSUE_DETECTED:
        artifacts = ", ".join(p.get("affected_artifacts", []) or []) or "unknown sources"
        return f"{p.get('title', 'Conflict')} ({p.get('issue_type', '')}) across {artifacts}"
    if event.event == PARSE_FAILED:
        return f"Parse failed for {p.get('filename', 'artifact')}: {p.get('error', 'unknown error')}"
    if event.event == METRIC_CANDIDATE_DISCOVERED:
        return f"{p.get('proposed_name', 'metric')} ({p.get('metric_family', 'n/a')})"
    if event.event == METRIC_APPROVED:
        return f"{p.get('canonical_name', 'metric')} approved by {p.get('approved_by', 'someone')}"
    if event.event == METRIC_RUN_COMPLETED:
        return f"Run for {p.get('canonical_name', 'metric')} finished: {p.get('status', 'unknown')}"
    if event.event in {FILE_ADDED, FILE_MODIFIED, FILE_REMOVED}:
        return p.get("path", "unknown path")
    return event.event


def _fields_for_event(event: Event) -> list[tuple[str, str]]:
    p = event.payload
    if event.event == ISSUE_DETECTED:
        return [
            ("Type", p.get("issue_type", "")),
            ("Severity", str(p.get("severity", ""))),
            ("Affected", ", ".join(p.get("affected_artifacts", []) or []) or "-"),
        ]
    if event.event == PARSE_FAILED:
        return [("Artifact", p.get("filename", "")), ("Error", p.get("error", ""))]
    if event.event == METRIC_CANDIDATE_DISCOVERED:
        return [
            ("Family", p.get("metric_family", "")),
            ("Entity", p.get("entity", "") or "-"),
            ("Grain", p.get("grain", "") or "-"),
        ]
    if event.event == METRIC_APPROVED:
        return [("Metric", p.get("canonical_name", "")), ("Approved by", p.get("approved_by", ""))]
    if event.event == METRIC_RUN_COMPLETED:
        return [("Metric", p.get("canonical_name", "")), ("Status", p.get("status", ""))]
    if event.event in {FILE_ADDED, FILE_MODIFIED, FILE_REMOVED}:
        return [
            ("Path", p.get("path", "")),
            ("Hash", (p.get("content_hash") or "")[:12]),
        ]
    return []


# --- Slack ---

def slack_blocks_for_event(event: Event) -> list[dict[str, Any]]:
    fields = _fields_for_event(event)
    blocks: list[dict[str, Any]] = [
        {"type": "header", "text": {"type": "plain_text", "text": event_title(event)}},
        {"type": "section", "text": {"type": "mrkdwn", "text": event_summary(event)}},
    ]
    if fields:
        blocks.append(
            {
                "type": "section",
                "fields": [
                    {"type": "mrkdwn", "text": f"*{k}*\n{v}"} for k, v in fields
                ],
            }
        )
    blocks.append(
        {
            "type": "context",
            "elements": [
                {"type": "mrkdwn", "text": f"source: `{event.source}` · {event.ts.isoformat()}"}
            ],
        }
    )
    return blocks


def slack_blocks_for_metric(metric: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        {"type": "header", "text": {"type": "plain_text", "text": metric.get("canonical_name", "Metric")}},
        {"type": "section", "text": {"type": "mrkdwn", "text": metric_answer_markdown(metric)}},
    ]


def slack_blocks_for_search(query: str, results: list[dict[str, Any]]) -> list[dict[str, Any]]:
    if not results:
        return [{"type": "section", "text": {"type": "mrkdwn", "text": f"No results for `{query}`."}}]
    lines = [
        f"*{r.get('title')}* ({r.get('type')}) — {r.get('subtitle', '')}" for r in results[:8]
    ]
    return [
        {"type": "section", "text": {"type": "mrkdwn", "text": f"Results for `{query}`:"}},
        {"type": "section", "text": {"type": "mrkdwn", "text": "\n".join(lines)}},
    ]


# --- Teams (Adaptive Card via Incoming Webhook) ---

def teams_card_for_event(event: Event) -> dict[str, Any]:
    facts = [{"title": k, "value": v} for k, v in _fields_for_event(event)]
    card = {
        "type": "message",
        "attachments": [
            {
                "contentType": "application/vnd.microsoft.card.adaptive",
                "content": {
                    "type": "AdaptiveCard",
                    "$schema": "http://adaptivecards.io/schemas/adaptive-card.json",
                    "version": "1.4",
                    "body": [
                        {"type": "TextBlock", "size": "Medium", "weight": "Bolder", "text": event_title(event)},
                        {"type": "TextBlock", "wrap": True, "text": event_summary(event)},
                        {"type": "FactSet", "facts": facts},
                        {
                            "type": "TextBlock",
                            "isSubtle": True,
                            "spacing": "Small",
                            "text": f"source: {event.source} · {event.ts.isoformat()}",
                        },
                    ],
                },
            }
        ],
    }
    return card


def teams_text_card(title: str, text: str) -> dict[str, Any]:
    return {
        "type": "message",
        "attachments": [
            {
                "contentType": "application/vnd.microsoft.card.adaptive",
                "content": {
                    "type": "AdaptiveCard",
                    "$schema": "http://adaptivecards.io/schemas/adaptive-card.json",
                    "version": "1.4",
                    "body": [
                        {"type": "TextBlock", "size": "Medium", "weight": "Bolder", "text": title},
                        {"type": "TextBlock", "wrap": True, "text": text},
                    ],
                },
            }
        ],
    }


# --- Linear ---

def linear_issue_for_event(event: Event) -> tuple[str, str]:
    """Return (title, markdown description) for a Linear issue from an event."""
    p = event.payload
    title = f"[MetricGraph] {p.get('title', event_title(event))}"
    desc_lines = [
        p.get("explanation", "") or event_summary(event),
        "",
        f"- Issue type: `{p.get('issue_type', 'n/a')}`",
        f"- Severity: {p.get('severity', 'n/a')}",
        f"- Affected artifacts: {', '.join(p.get('affected_artifacts', []) or []) or 'n/a'}",
        "",
        "_Filed automatically by integration_hub from a MetricGraph conflict._",
    ]
    return title, "\n".join(desc_lines)


def metric_answer_markdown(metric: dict[str, Any]) -> str:
    """Markdown answer used for Linear comments and Slack/Teams metric replies."""
    name = metric.get("canonical_name", "Unknown metric")
    status = metric.get("status", "unknown")
    owner = metric.get("owner") or "unassigned"
    domain = metric.get("domain") or "-"
    entity = metric.get("entity") or "-"
    grain = metric.get("grain") or "-"
    desc = metric.get("description") or "_No description on record._"

    lines = [
        f"**{name}**  ·  status: `{status}`  ·  owner: {owner}",
        "",
        desc,
        "",
        f"- Domain: {domain}",
        f"- Entity / Grain: {entity} / {grain}",
        f"- Version: {metric.get('version', 1)}",
    ]

    specs = metric.get("specs") or []
    if specs:
        spec = specs[0]
        inputs = spec.get("required_inputs")
        if inputs:
            lines.append(f"- Required inputs: `{inputs}`")
        plan = spec.get("transformation_plan")
        if plan:
            lines.append(f"- Transformation: `{plan}`")
        if spec.get("approved_by"):
            lines.append(f"- Approved by: {spec['approved_by']}")
    return "\n".join(lines)


def metric_not_found_markdown(query: str) -> str:
    return (
        f"I couldn't find a metric matching **{query}** in the MetricGraph registry. "
        "Try the exact canonical name, or check the Discovery view for candidates."
    )
