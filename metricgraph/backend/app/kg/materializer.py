"""Knowledge graph materializer — builds workspace-scoped graph in Neo4j."""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.kg.neo4j_store import Neo4jStore
from app.models import (
    Artifact,
    FormulaImplementation,
    Issue,
    IngestSession,
    Metric,
    MetricClusterMember,
    MetricTag,
)


def materialize_workspace(db: Session, workspace_id: str, store: Neo4jStore | None = None) -> dict[str, int]:
    """Rebuild KG for a workspace from parse, registry, and SDK declared links."""
    kg = store or Neo4jStore()
    kg.ensure_constraints()
    kg.clear_workspace(workspace_id)

    node_count = 0
    edge_count = 0

    def upsert(node_type: str, external_ref: str, label: str, properties: dict | None = None) -> None:
        nonlocal node_count
        kg.upsert_node(workspace_id, node_type, external_ref, label, properties)
        node_count += 1

    def link(from_ref: str, to_ref: str, edge_type: str, source: str) -> None:
        nonlocal edge_count
        kg.link(workspace_id, from_ref, to_ref, edge_type, source)
        edge_count += 1

    artifacts = list(
        db.scalars(
            select(Artifact)
            .where(Artifact.workspace_id == workspace_id)
            .options(selectinload(Artifact.implementations).selectinload(FormulaImplementation.normalized))
        )
    )

    for artifact in artifacts:
        art_ref = f"artifact:{artifact.id}"
        upsert("artifact", art_ref, artifact.filename, {"status": artifact.status})
        for impl in artifact.implementations:
            formula_ref = f"formula:{impl.id}"
            upsert(
                "formula",
                formula_ref,
                impl.extracted_name,
                {"language": impl.language, "location": impl.location},
            )
            link(art_ref, formula_ref, "defined_in", "parse")

            for table in (impl.source_tables or {}).get("refs") or []:
                table_ref = f"table:{table}"
                upsert("table", table_ref, table)
                link(table_ref, formula_ref, "reads_from", "parse")

            for fn in (impl.referenced_functions or {}).get("functions") or []:
                fn_ref = f"function:{fn}"
                upsert("function", fn_ref, fn)
                link(formula_ref, fn_ref, "references", "parse")

    metrics = list(
        db.scalars(
            select(Metric)
            .where(Metric.workspace_id == workspace_id)
            .options(selectinload(Metric.tags))
        )
    )
    for metric in metrics:
        metric_ref = f"metric:{metric.id}"
        upsert(
            "metric",
            metric_ref,
            metric.canonical_name,
            {"domain": metric.domain, "status": metric.status},
        )
        for tag in metric.tags:
            tag_ref = f"tag:{tag.tag}"
            upsert("tag", tag_ref, tag.tag, {"digest": tag.digest})
            link(metric_ref, tag_ref, "published_as", "registry")

        for artifact in artifacts:
            for impl in artifact.implementations:
                if impl.extracted_name.lower() == metric.canonical_name.lower():
                    link(f"formula:{impl.id}", metric_ref, "published_as", "registry")

    members = list(
        db.scalars(
            select(MetricClusterMember).options(selectinload(MetricClusterMember.formula_implementation))
        )
    )
    impl_to_cluster: dict[str, list[MetricClusterMember]] = {}
    for member in members:
        impl_to_cluster.setdefault(member.formula_implementation_id, []).append(member)

    for impl_id, member_list in impl_to_cluster.items():
        if len(member_list) < 2:
            continue
        base_ref = f"formula:{impl_id}"
        for other in member_list:
            if other.formula_implementation_id == impl_id:
                continue
            other_ref = f"formula:{other.formula_implementation_id}"
            edge_type = "conflicts_with" if other.relationship_type == "conflicting" else "similar_to"
            link(base_ref, other_ref, edge_type, "parse")

    issues = list(db.scalars(select(Issue)))
    for issue in issues:
        if not issue.affected_artifacts:
            continue
        issue_ref = f"issue:{issue.id}"
        upsert(
            "issue",
            issue_ref,
            issue.title or issue.issue_type,
            {"severity": issue.severity, "explanation": issue.explanation},
        )
        for art_name in issue.affected_artifacts:
            art = next((a for a in artifacts if a.filename == art_name), None)
            if art:
                link(issue_ref, f"artifact:{art.id}", "conflicts_with", "parse")

    sessions = list(db.scalars(select(IngestSession).where(IngestSession.workspace_id == workspace_id)))
    for session in sessions:
        for declared in session.declared_links or []:
            metric_name = declared.get("metric") or declared.get("name")
            if not metric_name:
                continue
            metric = db.scalar(
                select(Metric)
                .where(Metric.workspace_id == workspace_id, Metric.canonical_name.ilike(metric_name))
                .limit(1)
            )
            if metric:
                metric_ref = f"metric:{metric.id}"
            else:
                metric_ref = f"concept:{metric_name}"
                upsert("concept", metric_ref, metric_name)

            if declared.get("uses_table"):
                table_ref = f"table:{declared['uses_table']}"
                upsert("table", table_ref, declared["uses_table"])
                link(table_ref, metric_ref, "reads_from", "sdk")
            if declared.get("steward_team"):
                team_ref = f"team:{declared['steward_team']}"
                upsert("team", team_ref, declared["steward_team"])
                link(metric_ref, team_ref, "stewards", "sdk")
            if declared.get("owned_by"):
                person_ref = f"person:{declared['owned_by']}"
                upsert("person", person_ref, declared["owned_by"])
                link(metric_ref, person_ref, "owned_by", "sdk")

    return {"nodes": node_count, "edges": edge_count}


def get_context_subgraph(
    db: Session,
    workspace_id: str,
    metric_id: str,
    depth: int = 2,
    store: Neo4jStore | None = None,
) -> dict:
    metric = db.get(Metric, metric_id)
    if not metric or metric.workspace_id != workspace_id:
        return {"nodes": [], "edges": []}
    kg = store or Neo4jStore()
    metric_ref = f"metric:{metric_id}"
    # Ensure root exists for metrics not yet materialized
    kg.upsert_node(
        workspace_id,
        "metric",
        metric_ref,
        metric.canonical_name,
        {"domain": metric.domain, "status": metric.status},
    )
    return kg.get_context_subgraph(workspace_id, metric_ref, depth=depth)


def get_impact_subgraph(db: Session, workspace_id: str, ref: str, store: Neo4jStore | None = None) -> dict:
    kg = store or Neo4jStore()
    return kg.get_impact_subgraph(workspace_id, ref)


def get_neighbors_subgraph(workspace_id: str, ref: str, store: Neo4jStore | None = None) -> dict:
    kg = store or Neo4jStore()
    return kg.get_neighbors(workspace_id, ref)
