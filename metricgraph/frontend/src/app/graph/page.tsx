"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { GraphView } from "@/components/GraphView";
import { useApiKey, v1Api } from "@/lib/api-v1";
import { api } from "@/lib/api";

export default function GraphOverviewPage() {
  const apiKey = useApiKey();
  const [stats, setStats] = useState({ nodes: 0, edges: 0 });
  const [metrics, setMetrics] = useState<any[]>([]);
  const [error, setError] = useState("");

  useEffect(() => {
    if (!apiKey) return;
    v1Api.graphStats(apiKey).then(setStats).catch((e) => setError(e.message));
    api.metrics().then(setMetrics).catch(() => {});
  }, [apiKey]);

  return (
    <div className="page-header">
      <div>
        <h1>Knowledge Graph</h1>
        <p className="page-subtitle">Neo4j workspace graph — metrics, lineage, stewards</p>
      </div>
      <div className="stat-row">
        <div className="stat-card">
          <span>Nodes</span>
          <strong>{stats.nodes}</strong>
        </div>
        <div className="stat-card">
          <span>Edges</span>
          <strong>{stats.edges}</strong>
        </div>
      </div>
      {error && <p className="error-text">{error}</p>}
      <div className="repo-grid">
        {metrics.slice(0, 12).map((m) => (
          <Link key={m.id} href={`/graph/metric/${m.id}`} className="repo-card">
            <strong>{m.canonical_name}</strong>
            <span>{m.status}</span>
          </Link>
        ))}
      </div>
    </div>
  );
}
