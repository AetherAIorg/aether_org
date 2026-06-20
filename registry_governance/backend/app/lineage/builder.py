from __future__ import annotations

from dataclasses import dataclass, field

from app.metricgraph_client import MetricGraphClient


@dataclass
class LineageNodeView:
    id: str
    node_type: str
    label: str
    external_ref: str | None


@dataclass
class LineageEdgeView:
    id: str
    from_node_id: str
    to_node_id: str
    edge_type: str


@dataclass
class LineageGraph:
    nodes: list[LineageNodeView] = field(default_factory=list)
    edges: list[LineageEdgeView] = field(default_factory=list)
    _counter: int = 0

    def add_node(self, node_type: str, label: str, external_ref: str | None) -> str:
        ref = external_ref or label
        for n in self.nodes:
            if n.node_type == node_type and n.external_ref == ref:
                return n.id
        self._counter += 1
        node_id = f"n{self._counter}"
        self.nodes.append(LineageNodeView(id=node_id, node_type=node_type, label=label, external_ref=ref))
        return node_id

    def link(self, from_id: str, to_id: str, edge_type: str) -> None:
        if from_id == to_id:
            return
        self._counter += 1
        self.edges.append(
            LineageEdgeView(id=f"e{self._counter}", from_node_id=from_id, to_node_id=to_id, edge_type=edge_type)
        )


def build_lineage_graph(
    asset_type: str,
    external_id: str,
    name: str,
    mg_payload: dict,
    client: MetricGraphClient,
) -> LineageGraph:
    graph = LineageGraph()
    root = graph.add_node(asset_type, name, external_id)

    if asset_type == "metric":
        for spec in mg_payload.get("specs") or []:
            fn_id = spec.get("calculation_function_id")
            if fn_id:
                fn_node = graph.add_node("function", f"function:{fn_id}", fn_id)
                graph.link(fn_node, root, "references")
        for tag in mg_payload.get("tags") or []:
            tag_node = graph.add_node("tag", f"tag:{tag.get('tag')}", tag.get("digest"))
            graph.link(root, tag_node, "published_as")

        for cand in client.list_candidates("IRR"):
            try:
                detail = client.get_candidate(cand["id"])
            except Exception:
                continue
            for impl in detail.get("implementations") or []:
                formula_id = graph.add_node(
                    "formula",
                    impl.get("extracted_name") or impl.get("id", "formula"),
                    impl.get("id"),
                )
                graph.link(formula_id, root, "published_as")
                art_name = impl.get("artifact_filename") or "artifact"
                art_id = graph.add_node("artifact", art_name, art_name)
                graph.link(art_id, formula_id, "defined_in")
                for table in (impl.get("dimensions") or {}).get("source_tables") or []:
                    table_id = graph.add_node("table", table, table)
                    graph.link(table_id, formula_id, "reads_from")

    elif asset_type == "artifact":
        formula_id = graph.add_node("formula", f"formulas in {name}", name)
        graph.link(root, formula_id, "defined_in")

    return graph
