from __future__ import annotations

import logging

import httpx
from sqlalchemy.orm import Session

from app.config import settings
from app.metricgraph_client import MetricGraphClient
from app.models import ActivityLog
from app.sync.bootstrap import sync_from_metricgraph

logger = logging.getLogger(__name__)


def _trigger_kg_materialize() -> None:
    url = settings.metricgraph_materialize_url
    if not url:
        return
    headers = {"Authorization": f"Bearer {settings.metricgraph_api_key}"} if settings.metricgraph_api_key else {}
    try:
        httpx.post(url, headers=headers, timeout=10.0)
    except Exception as exc:  # noqa: BLE001
        logger.warning("KG materialize trigger failed: %s", exc)


def handle_metricgraph_event(db: Session, event_type: str, payload: dict) -> None:
    client = MetricGraphClient(settings.metricgraph_base_url)
    try:
        metric_id = payload.get("metric_id")
        if event_type in {"metric.approved", "metric.tag.published", "metric.run.completed"} and metric_id:
            metric = client.get_metric(metric_id)
            tags = client.list_metric_tags(metric_id)
            from app.sync.bootstrap import _upsert_asset

            _upsert_asset(
                db,
                "metric",
                metric_id,
                metric.get("canonical_name", metric_id),
                metric.get("description"),
                metric.get("domain"),
                metric.get("owner"),
                {**metric, "tags": tags},
            )
        elif event_type == "issue.detected":
            sync_from_metricgraph(db, client)
        elif event_type == "metric.candidate.discovered":
            sync_from_metricgraph(db, client)
        db.add(
            ActivityLog(
                event_type=event_type,
                summary=f"Webhook {event_type}",
                payload=payload,
            )
        )
        db.commit()
        if event_type in {"metric.approved", "metric.tag.published", "graph.materialized"}:
            _trigger_kg_materialize()
    finally:
        client.close()
