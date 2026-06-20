from __future__ import annotations

import json
from typing import Annotated, Any

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.auth import AuthContext, require_roles
from app import events
from app.database import get_db
from app.kg.materializer import (
    get_context_subgraph,
    get_impact_subgraph,
    get_neighbors_subgraph,
    materialize_workspace,
)
from app.models import Artifact, IngestSession, Metric, ParseJob
from app.parsers import artifact_type_from_filename
from app.queue import enqueue_parse
from app.schemas import (
    ArtifactOut,
    ContextLinkBatchIn,
    GraphMaterializeOut,
    IngestSessionOut,
    LineageGraphOut,
)
from app.storage import upload_bytes

router = APIRouter(prefix="/api/v1", tags=["v1"])


def _artifact_out(artifact: Artifact) -> ArtifactOut:
    return ArtifactOut(
        id=artifact.id,
        filename=artifact.filename,
        artifact_type=artifact.artifact_type,
        owner=artifact.owner,
        storage_path=artifact.storage_path,
        status=artifact.status,
        uploaded_at=artifact.uploaded_at,
        object_count=artifact.object_count,
    )


@router.post("/ingest", response_model=IngestSessionOut)
async def ingest_files(
    files: list[UploadFile] = File(...),
    context: str | None = Form(None),
    session_id: str | None = Form(None),
    ctx: Annotated[AuthContext, Depends(require_roles("ingest", "admin"))] = None,
    db: Session = Depends(get_db),
):
    context_data: dict[str, Any] = {}
    if context:
        try:
            context_data = json.loads(context)
        except json.JSONDecodeError as exc:
            raise HTTPException(status_code=400, detail="Invalid context JSON") from exc

    session: IngestSession | None = None
    if session_id:
        session = db.get(IngestSession, session_id)
        if not session or session.workspace_id != ctx.workspace_id:
            raise HTTPException(status_code=404, detail="Ingest session not found")
    else:
        session = IngestSession(
            workspace_id=ctx.workspace_id,
            api_key_id=ctx.api_key_id,
            context=context_data,
            declared_links=[],
            status="open",
        )
        db.add(session)
        db.flush()

    if context_data and not session.context:
        session.context = context_data
    elif context_data:
        session.context = {**(session.context or {}), **context_data}

    parse_job_ids: list[str] = []
    artifacts_out: list[ArtifactOut] = []

    for upload in files:
        if not upload.filename:
            continue
        content = await upload.read()
        try:
            artifact_type = artifact_type_from_filename(upload.filename)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        key = upload_bytes(content, "artifacts", upload.filename)
        artifact = Artifact(
            workspace_id=ctx.workspace_id,
            ingest_session_id=session.id,
            filename=upload.filename,
            artifact_type=artifact_type,
            storage_path=key,
            status="uploaded",
            owner=(session.context or {}).get("owner"),
        )
        db.add(artifact)
        db.flush()
        job = ParseJob(artifact_id=artifact.id, status="queued")
        db.add(job)
        db.commit()
        rq_id = enqueue_parse(job.id, artifact.id)
        job.rq_job_id = rq_id
        db.commit()
        parse_job_ids.append(job.id)
        artifacts_out.append(_artifact_out(artifact))

    return IngestSessionOut(
        id=session.id,
        workspace_id=session.workspace_id,
        status=session.status,
        context=session.context,
        declared_links=session.declared_links or [],
        artifacts=artifacts_out,
        parse_jobs=parse_job_ids,
    )


@router.get("/ingest/{session_id}", response_model=IngestSessionOut)
def get_ingest_session(
    session_id: str,
    ctx: Annotated[AuthContext, Depends(require_roles("read", "ingest", "admin"))] = None,
    db: Session = Depends(get_db),
):
    session = db.get(IngestSession, session_id)
    if not session or session.workspace_id != ctx.workspace_id:
        raise HTTPException(status_code=404, detail="Ingest session not found")
    artifacts = list(
        db.scalars(select(Artifact).where(Artifact.ingest_session_id == session_id))
    )
    jobs = list(
        db.scalars(
            select(ParseJob)
            .join(Artifact, ParseJob.artifact_id == Artifact.id)
            .where(Artifact.ingest_session_id == session_id)
        )
    )
    return IngestSessionOut(
        id=session.id,
        workspace_id=session.workspace_id,
        status=session.status,
        context=session.context,
        declared_links=session.declared_links or [],
        artifacts=[_artifact_out(a) for a in artifacts],
        parse_jobs=[j.id for j in jobs],
        parse_job_statuses=[{"id": j.id, "status": j.status, "error": j.error} for j in jobs],
    )


@router.post("/context/links")
def add_context_links(
    body: ContextLinkBatchIn,
    ctx: Annotated[AuthContext, Depends(require_roles("ingest", "admin"))] = None,
    db: Session = Depends(get_db),
):
    session: IngestSession | None = None
    if body.session_id:
        session = db.get(IngestSession, body.session_id)
        if not session or session.workspace_id != ctx.workspace_id:
            raise HTTPException(status_code=404, detail="Ingest session not found")
    else:
        session = IngestSession(
            workspace_id=ctx.workspace_id,
            api_key_id=ctx.api_key_id,
            context={},
            declared_links=[],
            status="open",
        )
        db.add(session)
        db.flush()

    links = list(session.declared_links or [])
    for link in body.links:
        links.append(link.model_dump())
    session.declared_links = links
    db.commit()
    return {"session_id": session.id, "declared_links": session.declared_links}


@router.get("/graph/stats")
def graph_stats(
    ctx: Annotated[AuthContext, Depends(require_roles("read", "ingest", "admin"))] = None,
):
    from app.kg.neo4j_store import Neo4jStore

    store = Neo4jStore()
    return store.count_workspace(ctx.workspace_id)


@router.post("/graph/materialize", response_model=GraphMaterializeOut)
def materialize_graph(
    ctx: Annotated[AuthContext, Depends(require_roles("ingest", "admin"))] = None,
    db: Session = Depends(get_db),
):
    stats = materialize_workspace(db, ctx.workspace_id)
    events.emit(
        events.GRAPH_MATERIALIZED,
        {"workspace_id": ctx.workspace_id, **stats},
        event_id=events.make_event_id(events.GRAPH_MATERIALIZED, ctx.workspace_id),
    )
    return GraphMaterializeOut(workspace_id=ctx.workspace_id, **stats)


@router.get("/graph/context/{metric_id}", response_model=LineageGraphOut)
def graph_context(
    metric_id: str,
    depth: int = 2,
    ctx: Annotated[AuthContext, Depends(require_roles("read", "ingest", "admin"))] = None,
    db: Session = Depends(get_db),
):
    metric = db.get(Metric, metric_id)
    if not metric or metric.workspace_id != ctx.workspace_id:
        raise HTTPException(status_code=404, detail="Metric not found")
    data = get_context_subgraph(db, ctx.workspace_id, metric_id, depth=depth)
    return LineageGraphOut(**data)


@router.get("/graph/neighbors/{ref}", response_model=LineageGraphOut)
def graph_neighbors(
    ref: str,
    ctx: Annotated[AuthContext, Depends(require_roles("read", "ingest", "admin"))] = None,
    db: Session = Depends(get_db),
):
    data = get_neighbors_subgraph(ctx.workspace_id, ref)
    if not data["nodes"]:
        raise HTTPException(status_code=404, detail="Node not found")
    return LineageGraphOut(**data)


@router.get("/graph/impact/{ref}", response_model=LineageGraphOut)
def graph_impact(
    ref: str,
    ctx: Annotated[AuthContext, Depends(require_roles("read", "ingest", "admin"))] = None,
    db: Session = Depends(get_db),
):
    data = get_impact_subgraph(db, ctx.workspace_id, ref)
    return LineageGraphOut(**data)
