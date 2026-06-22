from __future__ import annotations

import json
import logging
from functools import lru_cache
from typing import Any
from uuid import uuid4

from neo4j import GraphDatabase, Driver

from app.config import settings

logger = logging.getLogger(__name__)

REL_TYPE = "KG_EDGE"


@lru_cache
def get_driver() -> Driver:
    return GraphDatabase.driver(
        settings.neo4j_uri,
        auth=(settings.neo4j_user, settings.neo4j_password),
    )


def close_driver() -> None:
    get_driver().close()
    get_driver.cache_clear()


class Neo4jStore:
    """Workspace-scoped knowledge graph in Neo4j."""

    def __init__(self, driver: Driver | None = None) -> None:
        self._driver = driver or get_driver()

    def ensure_constraints(self) -> None:
        with self._driver.session() as session:
            session.run(
                "CREATE CONSTRAINT kg_node_unique IF NOT EXISTS "
                "FOR (n:KgNode) REQUIRE (n.workspace_id, n.external_ref) IS UNIQUE"
            )

    def clear_workspace(self, workspace_id: str) -> None:
        with self._driver.session() as session:
            session.run(
                "MATCH (n:KgNode {workspace_id: $ws}) DETACH DELETE n",
                ws=workspace_id,
            )

    def upsert_node(
        self,
        workspace_id: str,
        node_type: str,
        external_ref: str,
        label: str,
        properties: dict | None = None,
    ) -> str:
        props = properties or {}
        with self._driver.session() as session:
            record = session.run(
                """
                MERGE (n:KgNode {workspace_id: $ws, external_ref: $ref})
                ON CREATE SET n.id = $id, n.node_type = $type, n.label = $label, n.properties = $props
                ON MATCH SET n.node_type = $type, n.label = $label, n.properties = $props
                RETURN n.id AS id
                """,
                ws=workspace_id,
                ref=external_ref,
                id=str(uuid4()),
                type=node_type,
                label=label,
                props=json.dumps(props),
            ).single()
            return record["id"]

    def link(
        self,
        workspace_id: str,
        from_ref: str,
        to_ref: str,
        edge_type: str,
        source: str,
        properties: dict | None = None,
    ) -> None:
        if from_ref == to_ref:
            return
        props = json.dumps(properties or {})
        with self._driver.session() as session:
            session.run(
                f"""
                MATCH (a:KgNode {{workspace_id: $ws, external_ref: $from_ref}})
                MATCH (b:KgNode {{workspace_id: $ws, external_ref: $to_ref}})
                MERGE (a)-[r:{REL_TYPE} {{edge_type: $edge_type, workspace_id: $ws}}]->(b)
                SET r.source = $source, r.properties = $props, r.id = coalesce(r.id, $rid)
                """,
                ws=workspace_id,
                from_ref=from_ref,
                to_ref=to_ref,
                edge_type=edge_type,
                source=source,
                props=props,
                rid=str(uuid4()),
            )

    def get_context_subgraph(self, workspace_id: str, metric_external_ref: str, depth: int = 2) -> dict:
        depth = max(1, min(int(depth), 5))
        query = f"""
                MATCH (root:KgNode {{workspace_id: $ws, external_ref: $ref}})
                OPTIONAL MATCH path = (root)-[:KG_EDGE*0..{depth}]-(n:KgNode)
                WHERE ALL(x IN nodes(path) WHERE x.workspace_id = $ws)
                WITH collect(DISTINCT root) + collect(DISTINCT n) AS ns,
                     [rel IN relationships(path) WHERE rel IS NOT NULL | rel] AS rels
                UNWIND ns AS node
                WITH collect(DISTINCT node) AS nodes, rels
                RETURN nodes, rels AS edges
                """
        with self._driver.session() as session:
            result = session.run(
                query,
                ws=workspace_id,
                ref=metric_external_ref,
            ).single()
            if not result or not result["nodes"]:
                return {"nodes": [], "edges": []}
            return self._format_graph(result["nodes"], result["edges"] or [])

    def get_neighbors(self, workspace_id: str, ref: str) -> dict:
        with self._driver.session() as session:
            result = session.run(
                """
                MATCH (root:KgNode {workspace_id: $ws})
                WHERE root.external_ref = $ref OR root.id = $ref
                OPTIONAL MATCH (root)-[r:KG_EDGE]-(n:KgNode {workspace_id: $ws})
                WITH collect(DISTINCT root) + collect(DISTINCT n) AS ns, collect(DISTINCT r) AS edges
                RETURN ns AS nodes, edges
                """,
                ws=workspace_id,
                ref=ref,
            ).single()
            if not result or not result["nodes"]:
                return {"nodes": [], "edges": []}
            return self._format_graph(result["nodes"], result["edges"] or [])

    def get_impact_subgraph(self, workspace_id: str, ref: str) -> dict:
        with self._driver.session() as session:
            result = session.run(
                """
                MATCH (start:KgNode {workspace_id: $ws})
                WHERE start.external_ref = $ref OR toLower(start.label) = toLower($ref)
                OPTIONAL MATCH (dependent:KgNode {workspace_id: $ws})-[r:KG_EDGE*1..3]->(start)
                WITH collect(DISTINCT start) + collect(DISTINCT dependent) AS ns,
                     collect(DISTINCT r) AS rel_lists
                WITH ns, reduce(acc = [], list IN rel_lists | acc + list) AS flat_edges
                RETURN ns AS nodes, flat_edges AS edges
                """,
                ws=workspace_id,
                ref=ref,
            ).single()
            if not result or not result["nodes"]:
                return {"nodes": [], "edges": []}
            edges = [e for sub in (result["edges"] or []) for e in sub if e is not None]
            return self._format_graph(result["nodes"], edges)

    def count_workspace(self, workspace_id: str) -> dict[str, int]:
        try:
            with self._driver.session() as session:
                record = session.run(
                    """
                    MATCH (n:KgNode {workspace_id: $ws})
                    OPTIONAL MATCH ()-[r:KG_EDGE {workspace_id: $ws}]->()
                    RETURN count(DISTINCT n) AS nodes, count(DISTINCT r) AS edges
                    """,
                    ws=workspace_id,
                ).single()
                return {"nodes": record["nodes"], "edges": record["edges"]}
        except Exception as exc:
            logger.warning("Neo4j unavailable for count_workspace: %s", exc)
            return {"nodes": 0, "edges": 0}

    @staticmethod
    def _format_graph(nodes: list, edges: list) -> dict[str, Any]:
        node_out = []
        seen_nodes: set[str] = set()
        for n in nodes:
            if n is None:
                continue
            nid = n.get("id")
            if not nid or nid in seen_nodes:
                continue
            seen_nodes.add(nid)
            props_raw = n.get("properties")
            props = json.loads(props_raw) if isinstance(props_raw, str) else (props_raw or {})
            node_out.append(
                {
                    "id": nid,
                    "node_type": n.get("node_type", ""),
                    "label": n.get("label", ""),
                    "external_ref": n.get("external_ref", ""),
                    "properties": props,
                }
            )

        id_by_element = {n.element_id: n.get("id") for n in nodes if n is not None and n.get("id")}
        edge_out = []
        seen_edges: set[str] = set()
        for r in edges:
            if r is None:
                continue
            rid = r.get("id") or f"{r.element_id}"
            if rid in seen_edges:
                continue
            seen_edges.add(rid)
            start_id = id_by_element.get(r.start_node.element_id)
            end_id = id_by_element.get(r.end_node.element_id)
            if not start_id or not end_id:
                continue
            props_raw = r.get("properties")
            props = json.loads(props_raw) if isinstance(props_raw, str) else (props_raw or {})
            edge_out.append(
                {
                    "id": rid,
                    "from_node_id": start_id,
                    "to_node_id": end_id,
                    "edge_type": r.get("edge_type", ""),
                    "source": r.get("source", ""),
                    "properties": props,
                }
            )
        return {"nodes": node_out, "edges": edge_out}
