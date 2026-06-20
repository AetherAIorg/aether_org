"""users and query activity

Revision ID: 004
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "004"
down_revision = "003"
branch_labels = None
depends_on = None


def upgrade() -> None:
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    existing = set(inspector.get_table_names())

    if "users" not in existing:
        op.create_table(
            "users",
            sa.Column("id", sa.String(), primary_key=True),
            sa.Column("email", sa.String(260), nullable=False),
            sa.Column("name", sa.String(160)),
            sa.Column("image", sa.String(512)),
            sa.Column("google_sub", sa.String(120)),
            sa.Column("created_at", sa.DateTime(timezone=True)),
        )
        op.create_index("ix_users_email", "users", ["email"], unique=True)

    if "workspace_members" not in existing:
        op.create_table(
            "workspace_members",
            sa.Column("id", sa.String(), primary_key=True),
            sa.Column("user_id", sa.String(), sa.ForeignKey("users.id")),
            sa.Column("workspace_id", sa.String(), sa.ForeignKey("workspaces.id")),
            sa.Column("role", sa.String(20), nullable=False),
            sa.Column("created_at", sa.DateTime(timezone=True)),
            sa.UniqueConstraint("user_id", "workspace_id", name="uq_workspace_member"),
        )

    if "query_events" not in existing:
        op.create_table(
            "query_events",
            sa.Column("id", sa.String(), primary_key=True),
            sa.Column("workspace_id", sa.String(), sa.ForeignKey("workspaces.id")),
            sa.Column("channel", sa.String(40), nullable=False),
            sa.Column("intent", sa.String(40), nullable=False),
            sa.Column("query_text", sa.Text(), nullable=False),
            sa.Column("answer_preview", sa.Text()),
            sa.Column("answer_full", sa.Text()),
            sa.Column("external_ref", sa.String(260)),
            sa.Column("external_url", sa.String(512)),
            sa.Column("author", sa.String(260)),
            sa.Column("metric_id", sa.String(), sa.ForeignKey("metrics.id")),
            sa.Column("graph_node_count", sa.Integer(), default=0),
            sa.Column("created_at", sa.DateTime(timezone=True)),
        )
        op.create_index("ix_query_events_workspace_id", "query_events", ["workspace_id"])
        op.create_index("ix_query_events_created_at", "query_events", ["created_at"])


def downgrade() -> None:
    op.drop_table("query_events")
    op.drop_table("workspace_members")
    op.drop_table("users")
