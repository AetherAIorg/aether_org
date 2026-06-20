"use client";

import { useParams } from "next/navigation";
import { useEffect, useState } from "react";
import { GraphView } from "@/components/GraphView";
import { useApiKey, v1Api, type GraphNode } from "@/lib/api-v1";
import { api } from "@/lib/api";

export default function MetricGraphPage() {
  const { id } = useParams<{ id: string }>();
  const apiKey = useApiKey();
  const [metric, setMetric] = useState<any>(null);
  const [nodes, setNodes] = useState<GraphNode[]>([]);
  const [edges, setEdges] = useState<any[]>([]);
  const [selected, setSelected] = useState<GraphNode | null>(null);

  useEffect(() => {
    if (!id) return;
    api.metric(id).then(setMetric).catch(() => {});
  }, [id]);

  useEffect(() => {
    if (!apiKey || !id) return;
    v1Api.graphContext(apiKey, id, 2).then((g) => {
      setNodes(g.nodes);
      setEdges(g.edges);
    });
  }, [apiKey, id]);

  return (
    <div>
      <div className="page-header">
        <h1>{metric?.canonical_name || "Metric graph"}</h1>
        <p className="page-subtitle">Context subgraph from Neo4j</p>
      </div>
      <div className="graph-layout">
        <GraphView nodes={nodes} edges={edges} height={520} onNodeClick={setSelected} />
        <aside className="graph-sidebar">
          <h3>Node detail</h3>
          {selected ? (
            <>
              <p className="pill">{selected.node_type}</p>
              <strong>{selected.label}</strong>
              <pre className="graph-props">{JSON.stringify(selected.properties || {}, null, 2)}</pre>
            </>
          ) : (
            <p className="text-margin-muted text-sm">Click a node to inspect</p>
          )}
        </aside>
      </div>
    </div>
  );
}
