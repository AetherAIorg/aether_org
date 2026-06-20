"use client";

import dynamic from "next/dynamic";
import { useMemo } from "react";
import type { GraphEdge, GraphNode } from "@/lib/api-v1";

const ForceGraph2D = dynamic(() => import("react-force-graph-2d"), { ssr: false });

const NODE_COLORS: Record<string, string> = {
  metric: "#3b82f6",
  formula: "#8b5cf6",
  table: "#22c55e",
  artifact: "#64748b",
  team: "#a855f7",
  person: "#ec4899",
  issue: "#ef4444",
  tag: "#06b6d4",
  function: "#f59e0b",
  concept: "#94a3b8",
};

type Props = {
  nodes: GraphNode[];
  edges: GraphEdge[];
  height?: number;
  onNodeClick?: (node: GraphNode) => void;
};

export function GraphView({ nodes, edges, height = 480, onNodeClick }: Props) {
  const graphData = useMemo(() => {
    const idMap = new Map(nodes.map((n) => [n.id, n]));
    return {
      nodes: nodes.map((n) => ({
        id: n.id,
        name: n.label,
        node_type: n.node_type,
        val: n.node_type === "metric" ? 8 : 4,
        raw: n,
      })),
      links: edges
        .filter((e) => idMap.has(e.from_node_id) && idMap.has(e.to_node_id))
        .map((e) => ({
          source: e.from_node_id,
          target: e.to_node_id,
          edge_type: e.edge_type,
        })),
    };
  }, [nodes, edges]);

  if (!nodes.length) {
    return (
      <div className="graph-empty" style={{ height }}>
        No graph data yet. Ingest sources and materialize the KG.
      </div>
    );
  }

  return (
    <div className="graph-canvas rounded-xl border border-margin-border overflow-hidden" style={{ height }}>
      <ForceGraph2D
        graphData={graphData}
        nodeLabel={(n: any) => `${n.node_type}: ${n.name}`}
        linkLabel={(l: any) => l.edge_type}
        nodeColor={(n: any) => NODE_COLORS[n.node_type] || "#64748b"}
        linkColor={() => "rgba(148,163,184,0.35)"}
        backgroundColor="#0b0f17"
        onNodeClick={(n: any) => onNodeClick?.(n.raw as GraphNode)}
      />
    </div>
  );
}
