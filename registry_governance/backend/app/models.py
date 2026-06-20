from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import DateTime, ForeignKey, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship


def new_id() -> str:
    return str(uuid.uuid4())


def now_utc() -> datetime:
    return datetime.now(timezone.utc)


class Person(Base):
    __tablename__ = "people"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=new_id)
    email: Mapped[str] = mapped_column(String(220), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(220), nullable=False)
    title: Mapped[str | None] = mapped_column(String(220), nullable=True)
    avatar_url: Mapped[str | None] = mapped_column(String(512), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now_utc)

    memberships: Mapped[list["TeamMembership"]] = relationship(back_populates="person")


class Team(Base):
    __tablename__ = "teams"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=new_id)
    slug: Mapped[str] = mapped_column(String(120), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(220), nullable=False)
    domain: Mapped[str | None] = mapped_column(String(120), nullable=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now_utc)

    memberships: Mapped[list["TeamMembership"]] = relationship(back_populates="team")


class TeamMembership(Base):
    __tablename__ = "team_memberships"
    __table_args__ = (UniqueConstraint("person_id", "team_id", name="uq_team_member"),)

    id: Mapped[str] = mapped_column(String, primary_key=True, default=new_id)
    person_id: Mapped[str] = mapped_column(ForeignKey("people.id"), index=True)
    team_id: Mapped[str] = mapped_column(ForeignKey("teams.id"), index=True)
    role: Mapped[str] = mapped_column(String(40), default="member")

    person: Mapped[Person] = relationship(back_populates="memberships")
    team: Mapped[Team] = relationship(back_populates="memberships")


class AssetMirror(Base):
    __tablename__ = "asset_mirrors"
    __table_args__ = (UniqueConstraint("asset_type", "external_id", name="uq_asset_mirror"),)

    id: Mapped[str] = mapped_column(String, primary_key=True, default=new_id)
    asset_type: Mapped[str] = mapped_column(String(40), index=True)
    external_id: Mapped[str] = mapped_column(String, index=True)
    name: Mapped[str] = mapped_column(String(260), nullable=False)
    summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    domain: Mapped[str | None] = mapped_column(String(120), nullable=True)
    owner_label: Mapped[str | None] = mapped_column(String(120), nullable=True)
    mg_payload: Mapped[dict] = mapped_column(JSONB, default=dict)
    synced_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now_utc)


class Stewardship(Base):
    __tablename__ = "stewardships"
    __table_args__ = (
        UniqueConstraint(
            "asset_type", "asset_external_id", "role", "person_id", "team_id",
            name="uq_stewardship",
        ),
    )

    id: Mapped[str] = mapped_column(String, primary_key=True, default=new_id)
    asset_type: Mapped[str] = mapped_column(String(40), index=True)
    asset_external_id: Mapped[str] = mapped_column(String, index=True)
    role: Mapped[str] = mapped_column(String(40), index=True)
    person_id: Mapped[str | None] = mapped_column(ForeignKey("people.id"), nullable=True)
    team_id: Mapped[str | None] = mapped_column(ForeignKey("teams.id"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now_utc)

    person: Mapped[Person | None] = relationship()
    team: Mapped[Team | None] = relationship()


class Annotation(Base):
    __tablename__ = "annotations"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=new_id)
    asset_type: Mapped[str] = mapped_column(String(40), index=True)
    asset_external_id: Mapped[str] = mapped_column(String, index=True)
    author_id: Mapped[str | None] = mapped_column(ForeignKey("people.id"), nullable=True)
    kind: Mapped[str] = mapped_column(String(40), default="note")
    title: Mapped[str] = mapped_column(String(260), default="")
    body: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now_utc)

    author: Mapped[Person | None] = relationship()


class Certification(Base):
    __tablename__ = "certifications"
    __table_args__ = (UniqueConstraint("asset_type", "asset_external_id", name="uq_certification"),)

    id: Mapped[str] = mapped_column(String, primary_key=True, default=new_id)
    asset_type: Mapped[str] = mapped_column(String(40), index=True)
    asset_external_id: Mapped[str] = mapped_column(String, index=True)
    level: Mapped[str] = mapped_column(String(40), default="draft", index=True)
    certified_by_id: Mapped[str | None] = mapped_column(ForeignKey("people.id"), nullable=True)
    certified_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    certified_by: Mapped[Person | None] = relationship()


class LineageNode(Base):
    __tablename__ = "lineage_nodes"
    __table_args__ = (UniqueConstraint("node_type", "external_ref", name="uq_lineage_node"),)

    id: Mapped[str] = mapped_column(String, primary_key=True, default=new_id)
    node_type: Mapped[str] = mapped_column(String(40), index=True)
    label: Mapped[str] = mapped_column(String(260), nullable=False)
    external_ref: Mapped[str | None] = mapped_column(String(260), nullable=True)


class LineageEdge(Base):
    __tablename__ = "lineage_edges"
    __table_args__ = (UniqueConstraint("from_node_id", "to_node_id", "edge_type", name="uq_lineage_edge"),)

    id: Mapped[str] = mapped_column(String, primary_key=True, default=new_id)
    from_node_id: Mapped[str] = mapped_column(ForeignKey("lineage_nodes.id"), index=True)
    to_node_id: Mapped[str] = mapped_column(ForeignKey("lineage_nodes.id"), index=True)
    edge_type: Mapped[str] = mapped_column(String(40), index=True)


class IssueMirror(Base):
    __tablename__ = "issue_mirrors"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=new_id)
    external_key: Mapped[str] = mapped_column(String(260), unique=True, index=True)
    issue_type: Mapped[str] = mapped_column(String(80), index=True)
    title: Mapped[str] = mapped_column(String(260), default="")
    explanation: Mapped[str] = mapped_column(Text, default="")
    severity: Mapped[str] = mapped_column(String(40), default="medium")
    status: Mapped[str] = mapped_column(String(40), default="open", index=True)
    assignee_id: Mapped[str | None] = mapped_column(ForeignKey("people.id"), nullable=True)
    linked_asset_type: Mapped[str | None] = mapped_column(String(40), nullable=True)
    linked_asset_external_id: Mapped[str | None] = mapped_column(String, nullable=True)
    mg_payload: Mapped[dict] = mapped_column(JSONB, default=dict)
    synced_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now_utc)

    assignee: Mapped[Person | None] = relationship()


class ActivityLog(Base):
    __tablename__ = "activity_log"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=new_id)
    event_type: Mapped[str] = mapped_column(String(80), index=True)
    summary: Mapped[str] = mapped_column(String(512), default="")
    payload: Mapped[dict] = mapped_column(JSONB, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now_utc)
