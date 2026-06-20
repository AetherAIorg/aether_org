from __future__ import annotations

import uuid

import pytest

from app.kg.materializer import materialize_workspace
from app.kg.neo4j_store import Neo4jStore
from app.models import Artifact, FormulaImplementation, Metric, Workspace


@pytest.fixture()
def db():
    from app.database import SessionLocal

    session = SessionLocal()
    try:
        yield session
    finally:
        session.rollback()
        session.close()


@pytest.fixture()
def neo4j_store():
    store = Neo4jStore()
    store.ensure_constraints()
    return store


def test_materialize_workspace_isolation(db, neo4j_store):
    suffix = uuid.uuid4().hex[:8]
    ws_a = Workspace(slug=f"test-a-{suffix}", name="A")
    ws_b = Workspace(slug=f"test-b-{suffix}", name="B")
    db.add_all([ws_a, ws_b])
    db.flush()

    art_a = Artifact(workspace_id=ws_a.id, filename="a.sql", artifact_type="sql", storage_path="k/a")
    art_b = Artifact(workspace_id=ws_b.id, filename="b.sql", artifact_type="sql", storage_path="k/b")
    db.add_all([art_a, art_b])
    db.flush()
    db.add(
        FormulaImplementation(
            artifact_id=art_a.id,
            language="sql",
            raw_formula="SELECT 1",
            location="L1",
            extracted_name="Metric A",
            source_tables={"refs": ["table_a"]},
        )
    )
    db.add(Metric(workspace_id=ws_a.id, canonical_name="Metric A", status="approved"))
    db.commit()

    stats_a = materialize_workspace(db, ws_a.id, store=neo4j_store)
    stats_b = materialize_workspace(db, ws_b.id, store=neo4j_store)
    assert stats_a["nodes"] > stats_b["nodes"]

    counts_a = neo4j_store.count_workspace(ws_a.id)
    counts_b = neo4j_store.count_workspace(ws_b.id)
    assert counts_a["nodes"] > counts_b["nodes"]

    neo4j_store.clear_workspace(ws_a.id)
    neo4j_store.clear_workspace(ws_b.id)
