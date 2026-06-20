"""auth workspace kg

Revision ID: 003
"""
from __future__ import annotations

import uuid

import sqlalchemy as sa
from alembic import op

revision = "003"
down_revision = "002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    existing = set(inspector.get_table_names())

    if "workspaces" not in existing:
        op.create_table(
            "workspaces",
            sa.Column("id", sa.String(), primary_key=True),
            sa.Column("slug", sa.String(80), nullable=False),
            sa.Column("name", sa.String(160), nullable=False),
            sa.Column("created_at", sa.DateTime(timezone=True)),
        )
        op.create_index("ix_workspaces_slug", "workspaces", ["slug"], unique=True)

    if "api_keys" not in existing:
        op.create_table(
            "api_keys",
            sa.Column("id", sa.String(), primary_key=True),
            sa.Column("workspace_id", sa.String(), sa.ForeignKey("workspaces.id")),
            sa.Column("key_hash", sa.String(64), nullable=False),
            sa.Column("name", sa.String(120), nullable=False),
            sa.Column("role", sa.String(20), nullable=False),
            sa.Column("created_at", sa.DateTime(timezone=True)),
            sa.Column("last_used_at", sa.DateTime(timezone=True)),
        )
        op.create_index("ix_api_keys_workspace_id", "api_keys", ["workspace_id"])
        op.create_index("ix_api_keys_key_hash", "api_keys", ["key_hash"], unique=True)

    if "ingest_sessions" not in existing:
        op.create_table(
            "ingest_sessions",
            sa.Column("id", sa.String(), primary_key=True),
            sa.Column("workspace_id", sa.String(), sa.ForeignKey("workspaces.id")),
            sa.Column("api_key_id", sa.String(), sa.ForeignKey("api_keys.id"), nullable=True),
            sa.Column("context", sa.JSON(), nullable=True),
            sa.Column("declared_links", sa.JSON(), nullable=True),
            sa.Column("status", sa.String(40), nullable=False),
            sa.Column("created_at", sa.DateTime(timezone=True)),
        )
        op.create_index("ix_ingest_sessions_workspace_id", "ingest_sessions", ["workspace_id"])

    if "kg_nodes" not in existing:
        op.create_table(
            "kg_nodes",
            sa.Column("id", sa.String(), primary_key=True),
            sa.Column("workspace_id", sa.String(), sa.ForeignKey("workspaces.id")),
            sa.Column("node_type", sa.String(40), nullable=False),
            sa.Column("external_ref", sa.String(260), nullable=False),
            sa.Column("label", sa.String(260), nullable=False),
            sa.Column("properties", sa.JSON(), nullable=True),
            sa.UniqueConstraint("workspace_id", "node_type", "external_ref", name="uq_kg_node_ref"),
        )
        op.create_index("ix_kg_nodes_workspace_id", "kg_nodes", ["workspace_id"])

    if "kg_edges" not in existing:
        op.create_table(
            "kg_edges",
            sa.Column("id", sa.String(), primary_key=True),
            sa.Column("workspace_id", sa.String(), sa.ForeignKey("workspaces.id")),
            sa.Column("from_node_id", sa.String(), sa.ForeignKey("kg_nodes.id")),
            sa.Column("to_node_id", sa.String(), sa.ForeignKey("kg_nodes.id")),
            sa.Column("edge_type", sa.String(40), nullable=False),
            sa.Column("properties", sa.JSON(), nullable=True),
            sa.Column("source", sa.String(40), nullable=False),
            sa.UniqueConstraint(
                "workspace_id", "from_node_id", "to_node_id", "edge_type", name="uq_kg_edge"
            ),
        )
        op.create_index("ix_kg_edges_workspace_id", "kg_edges", ["workspace_id"])

    artifact_cols = {c["name"] for c in inspector.get_columns("artifacts")}
    if "workspace_id" not in artifact_cols:
        op.add_column("artifacts", sa.Column("workspace_id", sa.String(), nullable=True))
        op.create_foreign_key("fk_artifacts_workspace_id", "artifacts", "workspaces", ["workspace_id"], ["id"])
        op.create_index("ix_artifacts_workspace_id", "artifacts", ["workspace_id"])
    if "ingest_session_id" not in artifact_cols:
        op.add_column("artifacts", sa.Column("ingest_session_id", sa.String(), nullable=True))
        op.create_foreign_key(
            "fk_artifacts_ingest_session_id", "artifacts", "ingest_sessions", ["ingest_session_id"], ["id"]
        )
        op.create_index("ix_artifacts_ingest_session_id", "artifacts", ["ingest_session_id"])

    metric_cols = {c["name"] for c in inspector.get_columns("metrics")}
    if "workspace_id" not in metric_cols:
        op.add_column("metrics", sa.Column("workspace_id", sa.String(), nullable=True))
        op.create_foreign_key("fk_metrics_workspace_id", "metrics", "workspaces", ["workspace_id"], ["id"])
        op.create_index("ix_metrics_workspace_id", "metrics", ["workspace_id"])

    # Default workspace for existing rows
    ws_row = conn.execute(sa.text("SELECT id FROM workspaces WHERE slug = 'default' LIMIT 1")).fetchone()
    if not ws_row:
        default_id = str(uuid.uuid4())
        conn.execute(
            sa.text(
                "INSERT INTO workspaces (id, slug, name, created_at) VALUES (:id, 'default', 'Default Workspace', NOW())"
            ),
            {"id": default_id},
        )
        wid = default_id
    else:
        wid = ws_row[0]
    conn.execute(sa.text("UPDATE artifacts SET workspace_id = :wid WHERE workspace_id IS NULL"), {"wid": wid})
    conn.execute(sa.text("UPDATE metrics SET workspace_id = :wid WHERE workspace_id IS NULL"), {"wid": wid})


def downgrade() -> None:
    op.drop_index("ix_metrics_workspace_id", table_name="metrics")
    op.drop_constraint("fk_metrics_workspace_id", "metrics", type_="foreignkey")
    op.drop_column("metrics", "workspace_id")

    op.drop_index("ix_artifacts_ingest_session_id", table_name="artifacts")
    op.drop_constraint("fk_artifacts_ingest_session_id", "artifacts", type_="foreignkey")
    op.drop_column("artifacts", "ingest_session_id")
    op.drop_index("ix_artifacts_workspace_id", table_name="artifacts")
    op.drop_constraint("fk_artifacts_workspace_id", "artifacts", type_="foreignkey")
    op.drop_column("artifacts", "workspace_id")

    op.drop_table("kg_edges")
    op.drop_table("kg_nodes")
    op.drop_table("ingest_sessions")
    op.drop_table("api_keys")
    op.drop_table("workspaces")
