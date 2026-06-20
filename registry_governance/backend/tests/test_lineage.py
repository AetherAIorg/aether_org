from __future__ import annotations

from unittest.mock import MagicMock

from app.lineage.builder import build_lineage_graph


def test_lineage_graph_for_metric():
    client = MagicMock()
    client.list_candidates.return_value = []
    graph = build_lineage_graph(
        "metric",
        "m1",
        "Fund IRR",
        {
            "specs": [{"calculation_function_id": "fn-1"}],
            "tags": [{"tag": "latest", "digest": "sha256:abc"}],
        },
        client,
    )
    assert len(graph.nodes) >= 3
    assert any(n.node_type == "function" for n in graph.nodes)
    assert any(n.node_type == "tag" for n in graph.nodes)


def test_lineage_graph_for_artifact():
    client = MagicMock()
    graph = build_lineage_graph("artifact", "a1", "fund.sql", {}, client)
    assert len(graph.nodes) >= 2
    assert graph.edges
