from __future__ import annotations

import os
from typing import Any

from app import formatting
from app.clients.margin_client import MarginClient


class ContextAgent:
    """Builds answers from registry + workspace-scoped KG subgraph."""

    def __init__(self, client: MarginClient, openrouter_api_key: str | None = None) -> None:
        self.client = client
        self.openrouter_api_key = openrouter_api_key

    def answer(self, intent: str, query: str) -> str:
        if intent == "search":
            results = self.client.search(query)
            if not results:
                return formatting.metric_not_found_markdown(query)
            lines = [f"Results for **{query}**:", ""]
            lines += [
                f"- **{r.get('title')}** ({r.get('type')}) — {r.get('subtitle', '')}"
                for r in results[:8]
            ]
            return "\n".join(lines)

        if intent == "impact":
            try:
                graph = self.client.graph_impact(query)
            except Exception:
                return formatting.metric_not_found_markdown(query)
            return self._format_impact(query, graph)

        metric = self.client.find_metric_by_name(query)
        if not metric and intent not in {"impact"}:
            return formatting.metric_not_found_markdown(query)

        if intent == "definition":
            return formatting.metric_answer_markdown(metric)

        graph: dict[str, Any] = {}
        if metric:
            try:
                graph = self.client.get_graph_context(metric["id"])
            except Exception:
                graph = {}

        if intent == "context":
            return self._format_context(metric, graph)
        if intent == "stewardship":
            return self._format_stewardship(metric, graph)
        if intent == "conflicts":
            return self._format_conflicts(metric, graph)

        return formatting.metric_answer_markdown(metric)

    def _format_context(self, metric: dict, graph: dict) -> str:
        lines = [f"**Context: {metric.get('canonical_name')}**", ""]
        lines.append(formatting.metric_answer_markdown(metric))
        if graph.get("nodes"):
            lines.append("")
            lines.append("**Knowledge graph**")
            for node in graph.get("nodes", [])[:12]:
                lines.append(f"- `{node.get('node_type')}` **{node.get('label')}**")
            edge_types = sorted({e.get("edge_type") for e in graph.get("edges", [])})
            if edge_types:
                lines.append("")
                lines.append(f"Relationships: {', '.join(edge_types)}")
        return "\n".join(lines)

    def _format_stewardship(self, metric: dict, graph: dict) -> str:
        stewards = [
            n.get("label")
            for n in graph.get("nodes", [])
            if n.get("node_type") in {"team", "person"}
        ]
        owner = metric.get("owner") or "unknown"
        lines = [f"**Stewardship: {metric.get('canonical_name')}**", "", f"Owner: {owner}"]
        if stewards:
            lines.append("Stewards / teams:")
            lines.extend(f"- {s}" for s in stewards)
        else:
            lines.append("_No stewardship edges in KG yet._")
        return "\n".join(lines)

    def _format_conflicts(self, metric: dict, graph: dict) -> str:
        conflict_edges = [e for e in graph.get("edges", []) if e.get("edge_type") == "conflicts_with"]
        lines = [f"**Conflicts: {metric.get('canonical_name')}**", ""]
        if not conflict_edges:
            lines.append("_No conflict edges found in KG._")
            return "\n".join(lines)
        node_by_id = {n["id"]: n for n in graph.get("nodes", [])}
        for edge in conflict_edges[:8]:
            other = node_by_id.get(edge.get("from_node_id")) or node_by_id.get(edge.get("to_node_id"))
            if other:
                lines.append(f"- conflicts with **{other.get('label')}**")
        return "\n".join(lines)

    def _format_impact(self, ref: str, graph: dict) -> str:
        lines = [f"**Impact: {ref}**", ""]
        formulas = [n for n in graph.get("nodes", []) if n.get("node_type") == "formula"]
        metrics = [n for n in graph.get("nodes", []) if n.get("node_type") == "metric"]
        if formulas:
            lines.append("Formulas:")
            lines.extend(f"- {f.get('label')}" for f in formulas[:10])
        if metrics:
            lines.append("")
            lines.append("Metrics:")
            lines.extend(f"- {m.get('label')}" for m in metrics[:10])
        if not formulas and not metrics:
            lines.append("_No downstream usage found in KG._")
        return "\n".join(lines)
