"""initial governance schema

Revision ID: 001
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "people",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("email", sa.String(220), nullable=False, unique=True),
        sa.Column("name", sa.String(220), nullable=False),
        sa.Column("title", sa.String(220)),
        sa.Column("avatar_url", sa.String(512)),
        sa.Column("created_at", sa.DateTime(timezone=True)),
    )
    op.create_table(
        "teams",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("slug", sa.String(120), nullable=False, unique=True),
        sa.Column("name", sa.String(220), nullable=False),
        sa.Column("domain", sa.String(120)),
        sa.Column("description", sa.Text()),
        sa.Column("created_at", sa.DateTime(timezone=True)),
    )
    op.create_table(
        "team_memberships",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("person_id", sa.String(), sa.ForeignKey("people.id")),
        sa.Column("team_id", sa.String(), sa.ForeignKey("teams.id")),
        sa.Column("role", sa.String(40)),
        sa.UniqueConstraint("person_id", "team_id", name="uq_team_member"),
    )
    op.create_table(
        "asset_mirrors",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("asset_type", sa.String(40), index=True),
        sa.Column("external_id", sa.String(), index=True),
        sa.Column("name", sa.String(260), nullable=False),
        sa.Column("summary", sa.Text()),
        sa.Column("domain", sa.String(120)),
        sa.Column("owner_label", sa.String(120)),
        sa.Column("mg_payload", postgresql.JSONB(), server_default="{}"),
        sa.Column("synced_at", sa.DateTime(timezone=True)),
        sa.UniqueConstraint("asset_type", "external_id", name="uq_asset_mirror"),
    )
    op.create_table(
        "stewardships",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("asset_type", sa.String(40), index=True),
        sa.Column("asset_external_id", sa.String(), index=True),
        sa.Column("role", sa.String(40), index=True),
        sa.Column("person_id", sa.String(), sa.ForeignKey("people.id")),
        sa.Column("team_id", sa.String(), sa.ForeignKey("teams.id")),
        sa.Column("created_at", sa.DateTime(timezone=True)),
    )
    op.create_table(
        "annotations",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("asset_type", sa.String(40), index=True),
        sa.Column("asset_external_id", sa.String(), index=True),
        sa.Column("author_id", sa.String(), sa.ForeignKey("people.id")),
        sa.Column("kind", sa.String(40)),
        sa.Column("title", sa.String(260)),
        sa.Column("body", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True)),
    )
    op.create_table(
        "certifications",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("asset_type", sa.String(40), index=True),
        sa.Column("asset_external_id", sa.String(), index=True),
        sa.Column("level", sa.String(40), index=True),
        sa.Column("certified_by_id", sa.String(), sa.ForeignKey("people.id")),
        sa.Column("certified_at", sa.DateTime(timezone=True)),
        sa.Column("notes", sa.Text()),
        sa.UniqueConstraint("asset_type", "asset_external_id", name="uq_certification"),
    )
    op.create_table(
        "lineage_nodes",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("node_type", sa.String(40), index=True),
        sa.Column("label", sa.String(260), nullable=False),
        sa.Column("external_ref", sa.String(260)),
        sa.UniqueConstraint("node_type", "external_ref", name="uq_lineage_node"),
    )
    op.create_table(
        "lineage_edges",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("from_node_id", sa.String(), sa.ForeignKey("lineage_nodes.id")),
        sa.Column("to_node_id", sa.String(), sa.ForeignKey("lineage_nodes.id")),
        sa.Column("edge_type", sa.String(40), index=True),
        sa.UniqueConstraint("from_node_id", "to_node_id", "edge_type", name="uq_lineage_edge"),
    )
    op.create_table(
        "issue_mirrors",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("external_key", sa.String(260), unique=True, index=True),
        sa.Column("issue_type", sa.String(80), index=True),
        sa.Column("title", sa.String(260)),
        sa.Column("explanation", sa.Text()),
        sa.Column("severity", sa.String(40)),
        sa.Column("status", sa.String(40), index=True),
        sa.Column("assignee_id", sa.String(), sa.ForeignKey("people.id")),
        sa.Column("linked_asset_type", sa.String(40)),
        sa.Column("linked_asset_external_id", sa.String()),
        sa.Column("mg_payload", postgresql.JSONB(), server_default="{}"),
        sa.Column("synced_at", sa.DateTime(timezone=True)),
    )
    op.create_table(
        "activity_log",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("event_type", sa.String(80), index=True),
        sa.Column("summary", sa.String(512)),
        sa.Column("payload", postgresql.JSONB(), server_default="{}"),
        sa.Column("created_at", sa.DateTime(timezone=True)),
    )


def downgrade() -> None:
    for t in (
        "activity_log",
        "issue_mirrors",
        "lineage_edges",
        "lineage_nodes",
        "certifications",
        "annotations",
        "stewardships",
        "asset_mirrors",
        "team_memberships",
        "teams",
        "people",
    ):
        op.drop_table(t)
