from app.lineage.builder import LineageGraph


def test_lineage_dedupes_nodes():
    graph = LineageGraph()
    a = graph.add_node("table", "fund_cashflows", "fund_cashflows")
    b = graph.add_node("table", "fund_cashflows", "fund_cashflows")
    assert a == b
    assert len(graph.nodes) == 1
