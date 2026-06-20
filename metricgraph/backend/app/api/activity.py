from __future__ import annotations

from datetime import datetime
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy import desc, func, select
from sqlalchemy.orm import Session

from app.auth import AuthContext, require_roles
from app.database import get_db
from app.models import QueryEvent

router = APIRouter(prefix="/api/v1/activity", tags=["activity"])


class QueryEventIn(BaseModel):
    channel: str
    intent: str
    query_text: str
    answer_preview: str = ""
    answer_full: str | None = None
    external_ref: str | None = None
    external_url: str | None = None
    author: str | None = None
    metric_id: str | None = None
    graph_node_count: int = 0


class QueryEventOut(BaseModel):
    id: str
    workspace_id: str
    channel: str
    intent: str
    query_text: str
    answer_preview: str
    external_ref: str | None
    external_url: str | None
    author: str | None
    metric_id: str | None
    graph_node_count: int
    created_at: datetime


class QueryEventDetailOut(QueryEventOut):
    answer_full: str | None


class QueryListOut(BaseModel):
    total: int
    items: list[QueryEventOut]


@router.post("/queries", response_model=QueryEventOut)
def create_query_event(
    body: QueryEventIn,
    ctx: Annotated[AuthContext, Depends(require_roles("read", "ingest", "admin"))],
    db: Session = Depends(get_db),
):
    preview = body.answer_preview or (body.answer_full or "")[:500]
    event = QueryEvent(
        workspace_id=ctx.workspace_id,
        channel=body.channel,
        intent=body.intent,
        query_text=body.query_text,
        answer_preview=preview,
        answer_full=body.answer_full,
        external_ref=body.external_ref,
        external_url=body.external_url,
        author=body.author,
        metric_id=body.metric_id,
        graph_node_count=body.graph_node_count,
    )
    db.add(event)
    db.commit()
    db.refresh(event)
    return QueryEventOut.model_validate(event, from_attributes=True)


@router.get("/queries", response_model=QueryListOut)
def list_query_events(
    ctx: Annotated[AuthContext, Depends(require_roles("read", "ingest", "admin"))],
    db: Session = Depends(get_db),
    channel: str | None = None,
    intent: str | None = None,
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
):
    q = select(QueryEvent).where(QueryEvent.workspace_id == ctx.workspace_id)
    if channel:
        q = q.where(QueryEvent.channel == channel)
    if intent:
        q = q.where(QueryEvent.intent == intent)
    total = db.scalar(
        select(func.count()).select_from(q.subquery())
    ) or 0
    items = list(
        db.scalars(q.order_by(desc(QueryEvent.created_at)).offset(offset).limit(limit))
    )
    return QueryListOut(
        total=total,
        items=[QueryEventOut.model_validate(i, from_attributes=True) for i in items],
    )


@router.get("/queries/{event_id}", response_model=QueryEventDetailOut)
def get_query_event(
    event_id: str,
    ctx: Annotated[AuthContext, Depends(require_roles("read", "ingest", "admin"))],
    db: Session = Depends(get_db),
):
    event = db.get(QueryEvent, event_id)
    if not event or event.workspace_id != ctx.workspace_id:
        raise HTTPException(status_code=404, detail="Query event not found")
    return QueryEventDetailOut.model_validate(event, from_attributes=True)
