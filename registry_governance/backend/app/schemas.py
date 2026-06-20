from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class PersonIn(BaseModel):
    email: str
    name: str
    title: str | None = None
    avatar_url: str | None = None


class PersonOut(BaseModel):
    id: str
    email: str
    name: str
    title: str | None
    avatar_url: str | None
    created_at: datetime


class TeamIn(BaseModel):
    slug: str
    name: str
    domain: str | None = None
    description: str | None = None


class TeamOut(BaseModel):
    id: str
    slug: str
    name: str
    domain: str | None
    description: str | None
    member_count: int = 0
    created_at: datetime


class TeamMemberIn(BaseModel):
    person_id: str
    role: str = "member"


class StewardshipIn(BaseModel):
    asset_type: str
    asset_external_id: str
    role: str
    person_id: str | None = None
    team_id: str | None = None


class StewardshipOut(BaseModel):
    id: str
    asset_type: str
    asset_external_id: str
    role: str
    person_id: str | None
    person_name: str | None = None
    team_id: str | None
    team_name: str | None = None


class AnnotationIn(BaseModel):
    asset_type: str
    asset_external_id: str
    kind: str = "note"
    title: str = ""
    body: str


class AnnotationOut(BaseModel):
    id: str
    asset_type: str
    asset_external_id: str
    kind: str
    title: str
    body: str
    author_id: str | None
    author_name: str | None = None
    created_at: datetime


class CertificationIn(BaseModel):
    asset_type: str
    asset_external_id: str
    level: str
    notes: str | None = None


class CertificationOut(BaseModel):
    asset_type: str
    asset_external_id: str
    level: str
    certified_by_id: str | None
    certified_by_name: str | None = None
    certified_at: datetime | None
    notes: str | None


class AssetMirrorOut(BaseModel):
    id: str
    asset_type: str
    external_id: str
    name: str
    summary: str | None
    domain: str | None
    owner_label: str | None
    synced_at: datetime
    certification: CertificationOut | None = None
    stewardship: list[StewardshipOut] = Field(default_factory=list)


class CatalogItemOut(BaseModel):
    asset_type: str
    external_id: str
    name: str
    summary: str | None
    domain: str | None
    certification_level: str | None = None
    owner_label: str | None = None
    latest_tag: str | None = None


class AssetHubOut(BaseModel):
    asset: AssetMirrorOut
    mg_payload: dict[str, Any]
    annotations: list[AnnotationOut] = Field(default_factory=list)
    lineage_summary: dict[str, Any] = Field(default_factory=dict)
    registry_url: str | None = None


class LineageNodeOut(BaseModel):
    id: str
    node_type: str
    label: str
    external_ref: str | None


class LineageEdgeOut(BaseModel):
    id: str
    from_node_id: str
    to_node_id: str
    edge_type: str


class LineageOut(BaseModel):
    nodes: list[LineageNodeOut]
    edges: list[LineageEdgeOut]


class IssueOut(BaseModel):
    id: str
    external_key: str
    issue_type: str
    title: str
    explanation: str
    severity: str
    status: str
    assignee_id: str | None
    assignee_name: str | None = None
    linked_asset_type: str | None
    linked_asset_external_id: str | None
    synced_at: datetime


class IssuePatchIn(BaseModel):
    status: str | None = None
    assignee_id: str | None = None


class TeamWorkspaceOut(BaseModel):
    team: TeamOut
    members: list[PersonOut]
    assets: list[CatalogItemOut]
    open_issues: list[IssueOut]
    recent_activity: list[dict[str, Any]] = Field(default_factory=list)


class SyncResultOut(BaseModel):
    metrics: int
    artifacts: int
    functions: int
    candidates: int
    issues: int
    stewardship_seeded: int
