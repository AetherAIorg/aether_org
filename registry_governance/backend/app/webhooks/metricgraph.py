from __future__ import annotations

from fastapi import APIRouter, Depends, Header, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.config import settings
from app.database import get_db
from app.sync.incremental import handle_metricgraph_event

router = APIRouter()


class WebhookEnvelope(BaseModel):
    source: str
    event: str
    id: str | None = None
    ts: str | None = None
    payload: dict = {}


@router.post("/webhooks/metricgraph")
def metricgraph_webhook(
    body: WebhookEnvelope,
    db: Session = Depends(get_db),
    x_hub_secret: str | None = Header(default=None, alias="X-Hub-Secret"),
):
    if settings.webhook_secret and x_hub_secret != settings.webhook_secret:
        raise HTTPException(status_code=401, detail="Invalid webhook secret")
    handle_metricgraph_event(db, body.event, body.payload)
    return {"ok": True}
