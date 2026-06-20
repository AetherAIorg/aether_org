from __future__ import annotations

from contextlib import asynccontextmanager
from datetime import datetime, timezone

from fastapi import Depends, FastAPI, Header, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session, selectinload

from app.config import settings
from app.database import SessionLocal, get_db
from app.lineage.builder import build_lineage_graph
from app.metricgraph_client import MetricGraphClient
from app.models import (
    ActivityLog,
    Annotation,
    AssetMirror,
    Certification,
    IssueMirror,
    Person,
    Stewardship,
    Team,
    TeamMembership,
)
from app.schemas import (
    AnnotationIn,
    AnnotationOut,
    AssetHubOut,
    AssetMirrorOut,
    CatalogItemOut,
    CertificationIn,
    CertificationOut,
    IssueOut,
    IssuePatchIn,
    LineageEdgeOut,
    LineageNodeOut,
    LineageOut,
    PersonIn,
    PersonOut,
    StewardshipIn,
    StewardshipOut,
    SyncResultOut,
    TeamIn,
    TeamMemberIn,
    TeamOut,
    TeamWorkspaceOut,
)
from app.sync.bootstrap import sync_from_metricgraph
from app.webhooks.metricgraph import router as webhook_router


def _resolve_actor(db: Session, x_actor_email: str | None) -> Person | None:
    if not x_actor_email:
        return None
    return db.scalar(select(Person).where(Person.email == x_actor_email))


def _stewardship_out(s: Stewardship) -> StewardshipOut:
    return StewardshipOut(
        id=s.id,
        asset_type=s.asset_type,
        asset_external_id=s.asset_external_id,
        role=s.role,
        person_id=s.person_id,
        person_name=s.person.name if s.person else None,
        team_id=s.team_id,
        team_name=s.team.name if s.team else None,
    )


def _cert_out(c: Certification | None) -> CertificationOut | None:
    if not c:
        return None
    return CertificationOut(
        asset_type=c.asset_type,
        asset_external_id=c.asset_external_id,
        level=c.level,
        certified_by_id=c.certified_by_id,
        certified_by_name=c.certified_by.name if c.certified_by else None,
        certified_at=c.certified_at,
        notes=c.notes,
    )


def _asset_out(db: Session, asset: AssetMirror) -> AssetMirrorOut:
    cert = db.scalar(
        select(Certification)
        .where(
            Certification.asset_type == asset.asset_type,
            Certification.asset_external_id == asset.external_id,
        )
        .options(selectinload(Certification.certified_by))
    )
    stewards = list(
        db.scalars(
            select(Stewardship)
            .where(
                Stewardship.asset_type == asset.asset_type,
                Stewardship.asset_external_id == asset.external_id,
            )
            .options(selectinload(Stewardship.person), selectinload(Stewardship.team))
        )
    )
    return AssetMirrorOut(
        id=asset.id,
        asset_type=asset.asset_type,
        external_id=asset.external_id,
        name=asset.name,
        summary=asset.summary,
        domain=asset.domain,
        owner_label=asset.owner_label,
        synced_at=asset.synced_at,
        certification=_cert_out(cert),
        stewardship=[_stewardship_out(s) for s in stewards],
    )


@asynccontextmanager
async def lifespan(app: FastAPI):
    if settings.auto_sync_on_startup:
        db = SessionLocal()
        client = MetricGraphClient(settings.metricgraph_base_url)
        try:
            sync_from_metricgraph(db, client)
            from app.seed.run_seed import run_seed

            run_seed()
        except Exception:
            db.rollback()
        finally:
            client.close()
            db.close()
    yield


app = FastAPI(title="Margin Catalog", version="0.1.0", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[o.strip() for o in settings.cors_origins.split(",") if o.strip()],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.include_router(webhook_router)


@app.get("/api/health")
def health():
    return {"status": "ok", "service": "margin-catalog"}


@app.get("/api/people", response_model=list[PersonOut])
def list_people(db: Session = Depends(get_db)):
    return list(db.scalars(select(Person).order_by(Person.name)))


@app.post("/api/people", response_model=PersonOut)
def create_person(payload: PersonIn, db: Session = Depends(get_db)):
    if db.scalar(select(Person).where(Person.email == payload.email)):
        raise HTTPException(status_code=409, detail="Email already exists")
    person = Person(**payload.model_dump())
    db.add(person)
    db.commit()
    db.refresh(person)
    return person


@app.get("/api/teams", response_model=list[TeamOut])
def list_teams(db: Session = Depends(get_db)):
    teams = list(db.scalars(select(Team).order_by(Team.name)))
    out = []
    for t in teams:
        count = db.scalar(
            select(func.count()).select_from(TeamMembership).where(TeamMembership.team_id == t.id)
        )
        out.append(
            TeamOut(
                id=t.id,
                slug=t.slug,
                name=t.name,
                domain=t.domain,
                description=t.description,
                member_count=count or 0,
                created_at=t.created_at,
            )
        )
    return out


@app.post("/api/teams", response_model=TeamOut)
def create_team(payload: TeamIn, db: Session = Depends(get_db)):
    if db.scalar(select(Team).where(Team.slug == payload.slug)):
        raise HTTPException(status_code=409, detail="Slug already exists")
    team = Team(**payload.model_dump())
    db.add(team)
    db.commit()
    db.refresh(team)
    return TeamOut(
        id=team.id,
        slug=team.slug,
        name=team.name,
        domain=team.domain,
        description=team.description,
        member_count=0,
        created_at=team.created_at,
    )


@app.post("/api/teams/{team_id}/members", response_model=PersonOut)
def add_team_member(team_id: str, payload: TeamMemberIn, db: Session = Depends(get_db)):
    team = db.get(Team, team_id)
    person = db.get(Person, payload.person_id)
    if not team or not person:
        raise HTTPException(status_code=404, detail="Team or person not found")
    existing = db.scalar(
        select(TeamMembership).where(
            TeamMembership.team_id == team_id,
            TeamMembership.person_id == payload.person_id,
        )
    )
    if not existing:
        db.add(TeamMembership(team_id=team_id, person_id=payload.person_id, role=payload.role))
        db.commit()
    return person


@app.get("/api/teams/{team_id}/workspace", response_model=TeamWorkspaceOut)
def team_workspace(team_id: str, db: Session = Depends(get_db)):
    team = db.get(Team, team_id)
    if not team:
        raise HTTPException(status_code=404, detail="Team not found")
    members = [
        m.person
        for m in db.scalars(
            select(TeamMembership)
            .where(TeamMembership.team_id == team_id)
            .options(selectinload(TeamMembership.person))
        )
        if m.person
    ]
    steward_asset_ids = [
        s.asset_external_id
        for s in db.scalars(select(Stewardship).where(Stewardship.team_id == team_id))
    ]
    assets = []
    for aid in steward_asset_ids[:20]:
        asset = db.scalar(
            select(AssetMirror).where(AssetMirror.external_id == aid).limit(1)
        )
        if asset:
            cert = db.scalar(
                select(Certification).where(
                    Certification.asset_type == asset.asset_type,
                    Certification.asset_external_id == asset.external_id,
                )
            )
            payload = asset.mg_payload or {}
            assets.append(
                CatalogItemOut(
                    asset_type=asset.asset_type,
                    external_id=asset.external_id,
                    name=asset.name,
                    summary=asset.summary,
                    domain=asset.domain,
                    certification_level=cert.level if cert else None,
                    owner_label=asset.owner_label,
                    latest_tag=payload.get("latest_tag"),
                )
            )
    issues = [
        IssueOut(
            id=i.id,
            external_key=i.external_key,
            issue_type=i.issue_type,
            title=i.title,
            explanation=i.explanation,
            severity=i.severity,
            status=i.status,
            assignee_id=i.assignee_id,
            assignee_name=i.assignee.name if i.assignee else None,
            linked_asset_type=i.linked_asset_type,
            linked_asset_external_id=i.linked_asset_external_id,
            synced_at=i.synced_at,
        )
        for i in db.scalars(select(IssueMirror).where(IssueMirror.status != "resolved").limit(20))
    ]
    activity = [
        {"event_type": a.event_type, "summary": a.summary, "created_at": a.created_at.isoformat()}
        for a in db.scalars(select(ActivityLog).order_by(ActivityLog.created_at.desc()).limit(10))
    ]
    count = db.scalar(
        select(func.count()).select_from(TeamMembership).where(TeamMembership.team_id == team_id)
    )
    return TeamWorkspaceOut(
        team=TeamOut(
            id=team.id,
            slug=team.slug,
            name=team.name,
            domain=team.domain,
            description=team.description,
            member_count=count or 0,
            created_at=team.created_at,
        ),
        members=members,
        assets=assets,
        open_issues=issues,
        recent_activity=activity,
    )


@app.get("/api/teams/by-slug/{slug}", response_model=TeamOut)
def get_team_by_slug(slug: str, db: Session = Depends(get_db)):
    team = db.scalar(select(Team).where(Team.slug == slug))
    if not team:
        raise HTTPException(status_code=404, detail="Team not found")
    count = db.scalar(
        select(func.count()).select_from(TeamMembership).where(TeamMembership.team_id == team.id)
    )
    return TeamOut(
        id=team.id,
        slug=team.slug,
        name=team.name,
        domain=team.domain,
        description=team.description,
        member_count=count or 0,
        created_at=team.created_at,
    )


@app.get("/api/catalog", response_model=list[CatalogItemOut])
def catalog_search(
    q: str | None = None,
    team: str | None = None,
    certification: str | None = None,
    domain: str | None = None,
    db: Session = Depends(get_db),
):
    query = select(AssetMirror)
    if q:
        term = f"%{q.lower()}%"
        query = query.where(
            or_(func.lower(AssetMirror.name).like(term), func.lower(AssetMirror.summary).like(term))
        )
    if domain:
        query = query.where(AssetMirror.domain == domain)
    assets = list(db.scalars(query.order_by(AssetMirror.name).limit(100)))
    out = []
    for asset in assets:
        cert = db.scalar(
            select(Certification).where(
                Certification.asset_type == asset.asset_type,
                Certification.asset_external_id == asset.external_id,
            )
        )
        if certification and (not cert or cert.level != certification):
            continue
        if team:
            team_row = db.scalar(select(Team).where(Team.slug == team))
            if not team_row:
                continue
            has = db.scalar(
                select(Stewardship).where(
                    Stewardship.team_id == team_row.id,
                    Stewardship.asset_external_id == asset.external_id,
                )
            )
            if not has:
                continue
        payload = asset.mg_payload or {}
        out.append(
            CatalogItemOut(
                asset_type=asset.asset_type,
                external_id=asset.external_id,
                name=asset.name,
                summary=asset.summary,
                domain=asset.domain,
                certification_level=cert.level if cert else None,
                owner_label=asset.owner_label,
                latest_tag=payload.get("latest_tag"),
            )
        )
    return out


@app.get("/api/assets/{asset_type}/{external_id}", response_model=AssetHubOut)
def get_asset_hub(asset_type: str, external_id: str, db: Session = Depends(get_db)):
    asset = db.scalar(
        select(AssetMirror).where(
            AssetMirror.asset_type == asset_type,
            AssetMirror.external_id == external_id,
        )
    )
    if not asset:
        raise HTTPException(status_code=404, detail="Asset not found")
    annotations = [
        AnnotationOut(
            id=a.id,
            asset_type=a.asset_type,
            asset_external_id=a.asset_external_id,
            kind=a.kind,
            title=a.title,
            body=a.body,
            author_id=a.author_id,
            author_name=a.author.name if a.author else None,
            created_at=a.created_at,
        )
        for a in db.scalars(
            select(Annotation).where(
                Annotation.asset_type == asset_type,
                Annotation.asset_external_id == external_id,
            ).order_by(Annotation.created_at.desc())
        )
    ]
    registry_url = None
    if asset_type == "metric":
        registry_url = f"{settings.registry_base_url.rstrip('/')}/metrics/{external_id}"
    client = MetricGraphClient(settings.metricgraph_base_url)
    try:
        graph = build_lineage_graph(
            asset_type, external_id, asset.name, asset.mg_payload or {}, client
        )
        lineage_summary = {
            "node_count": len(graph.nodes),
            "edge_count": len(graph.edges),
        }
    finally:
        client.close()
    return AssetHubOut(
        asset=_asset_out(db, asset),
        mg_payload=asset.mg_payload or {},
        annotations=annotations,
        lineage_summary=lineage_summary,
        registry_url=registry_url,
    )


@app.put("/api/stewardship", response_model=StewardshipOut)
def assign_stewardship(payload: StewardshipIn, db: Session = Depends(get_db)):
    if not payload.person_id and not payload.team_id:
        raise HTTPException(status_code=400, detail="person_id or team_id required")
    row = Stewardship(**payload.model_dump())
    db.add(row)
    db.commit()
    row = db.scalar(
        select(Stewardship)
        .where(Stewardship.id == row.id)
        .options(selectinload(Stewardship.person), selectinload(Stewardship.team))
    )
    return _stewardship_out(row)


@app.post("/api/annotations", response_model=AnnotationOut)
def create_annotation(
    payload: AnnotationIn,
    db: Session = Depends(get_db),
    x_actor_email: str | None = Header(default=None, alias="X-Actor-Email"),
):
    author = _resolve_actor(db, x_actor_email)
    row = Annotation(
        asset_type=payload.asset_type,
        asset_external_id=payload.asset_external_id,
        kind=payload.kind,
        title=payload.title,
        body=payload.body,
        author_id=author.id if author else None,
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return AnnotationOut(
        id=row.id,
        asset_type=row.asset_type,
        asset_external_id=row.asset_external_id,
        kind=row.kind,
        title=row.title,
        body=row.body,
        author_id=row.author_id,
        author_name=author.name if author else None,
        created_at=row.created_at,
    )


@app.put("/api/certification", response_model=CertificationOut)
def set_certification(
    payload: CertificationIn,
    db: Session = Depends(get_db),
    x_actor_email: str | None = Header(default=None, alias="X-Actor-Email"),
):
    actor = _resolve_actor(db, x_actor_email)
    row = db.scalar(
        select(Certification).where(
            Certification.asset_type == payload.asset_type,
            Certification.asset_external_id == payload.asset_external_id,
        )
    )
    if row:
        row.level = payload.level
        row.notes = payload.notes
        row.certified_by_id = actor.id if actor else row.certified_by_id
        row.certified_at = datetime.now(timezone.utc)
    else:
        row = Certification(
            asset_type=payload.asset_type,
            asset_external_id=payload.asset_external_id,
            level=payload.level,
            notes=payload.notes,
            certified_by_id=actor.id if actor else None,
            certified_at=datetime.now(timezone.utc),
        )
        db.add(row)
    db.commit()
    db.refresh(row)
    return _cert_out(row)


@app.get("/api/issues", response_model=list[IssueOut])
def list_issues(status: str | None = None, db: Session = Depends(get_db)):
    query = select(IssueMirror)
    if status:
        query = query.where(IssueMirror.status == status)
    rows = list(
        db.scalars(
            query.options(selectinload(IssueMirror.assignee)).order_by(IssueMirror.synced_at.desc())
        )
    )
    return [
        IssueOut(
            id=i.id,
            external_key=i.external_key,
            issue_type=i.issue_type,
            title=i.title,
            explanation=i.explanation,
            severity=i.severity,
            status=i.status,
            assignee_id=i.assignee_id,
            assignee_name=i.assignee.name if i.assignee else None,
            linked_asset_type=i.linked_asset_type,
            linked_asset_external_id=i.linked_asset_external_id,
            synced_at=i.synced_at,
        )
        for i in rows
    ]


@app.patch("/api/issues/{issue_id}", response_model=IssueOut)
def patch_issue(issue_id: str, payload: IssuePatchIn, db: Session = Depends(get_db)):
    row = db.scalar(
        select(IssueMirror).where(IssueMirror.id == issue_id).options(selectinload(IssueMirror.assignee))
    )
    if not row:
        raise HTTPException(status_code=404, detail="Issue not found")
    if payload.status is not None:
        row.status = payload.status
    if payload.assignee_id is not None:
        row.assignee_id = payload.assignee_id
    db.commit()
    db.refresh(row)
    return IssueOut(
        id=row.id,
        external_key=row.external_key,
        issue_type=row.issue_type,
        title=row.title,
        explanation=row.explanation,
        severity=row.severity,
        status=row.status,
        assignee_id=row.assignee_id,
        assignee_name=row.assignee.name if row.assignee else None,
        linked_asset_type=row.linked_asset_type,
        linked_asset_external_id=row.linked_asset_external_id,
        synced_at=row.synced_at,
    )


@app.get("/api/lineage/{asset_type}/{external_id}", response_model=LineageOut)
def get_lineage(asset_type: str, external_id: str, db: Session = Depends(get_db)):
    asset = db.scalar(
        select(AssetMirror).where(
            AssetMirror.asset_type == asset_type,
            AssetMirror.external_id == external_id,
        )
    )
    if not asset:
        raise HTTPException(status_code=404, detail="Asset not found")
    client = MetricGraphClient(settings.metricgraph_base_url)
    try:
        graph = build_lineage_graph(
            asset_type, external_id, asset.name, asset.mg_payload or {}, client
        )
    finally:
        client.close()
    return LineageOut(
        nodes=[LineageNodeOut(**n.__dict__) for n in graph.nodes],
        edges=[LineageEdgeOut(**e.__dict__) for e in graph.edges],
    )


@app.post("/api/sync/metricgraph", response_model=SyncResultOut)
def sync_metricgraph(db: Session = Depends(get_db)):
    client = MetricGraphClient(settings.metricgraph_base_url)
    try:
        counts = sync_from_metricgraph(db, client)
    finally:
        client.close()
    return SyncResultOut(**counts)
