"use client";

import { useEffect, useState } from "react";
import { useParams } from "next/navigation";
import Link from "next/link";
import { api } from "@/lib/api";
import { Breadcrumbs } from "@/components/CatalogShell";

type Tab = "overview" | "documentation" | "lineage" | "stewardship";

export default function AssetHubPage() {
  const params = useParams();
  const assetType = params.type as string;
  const externalId = params.id as string;
  const [hub, setHub] = useState<any>(null);
  const [lineage, setLineage] = useState<any>(null);
  const [tab, setTab] = useState<Tab>("overview");

  useEffect(() => {
    if (!assetType || !externalId) return;
    api.asset(assetType, externalId).then(setHub).catch(console.error);
  }, [assetType, externalId]);

  useEffect(() => {
    if (tab === "lineage" && assetType && externalId) {
      api.lineage(assetType, externalId).then(setLineage).catch(console.error);
    }
  }, [tab, assetType, externalId]);

  if (!hub) return <p className="muted">Loading…</p>;

  const cert = hub.asset.certification;

  return (
    <div>
      <Breadcrumbs items={[{ label: "Catalog", href: "/" }, { label: hub.asset.name }]} />
      <header className="page-header">
        <p className="eyebrow">{hub.asset.asset_type}</p>
        <h1>{hub.asset.name}</h1>
        <p className="muted">{hub.asset.summary}</p>
        <div className="page-header-actions">
          {cert && <span className={`pill ${cert.level === "certified" ? "pill-success" : "pill-warning"}`}>{cert.level}</span>}
          {hub.registry_url && (
            <a href={hub.registry_url} className="btn btn-secondary" target="_blank" rel="noreferrer">Open in Registry</a>
          )}
        </div>
      </header>

      <div className="tabs">
        {(["overview", "documentation", "lineage", "stewardship"] as Tab[]).map((t) => (
          <button key={t} type="button" className={`tab ${tab === t ? "active" : ""}`} onClick={() => setTab(t)}>
            {t.charAt(0).toUpperCase() + t.slice(1)}
          </button>
        ))}
      </div>

      {tab === "overview" && (
        <div className="panel">
          <p><strong>Domain:</strong> {hub.asset.domain || "—"}</p>
          <p><strong>Owner label:</strong> {hub.asset.owner_label || "—"}</p>
          <p><strong>Lineage:</strong> {hub.lineage_summary.node_count || 0} nodes, {hub.lineage_summary.edge_count || 0} edges</p>
          {hub.mg_payload?.latest_tag && <p><strong>Latest tag:</strong> {hub.mg_payload.latest_tag}</p>}
        </div>
      )}

      {tab === "documentation" && (
        <div className="list">
          {hub.annotations.map((a: any) => (
            <div key={a.id} className="card">
              <span className="pill">{a.kind}</span>
              <h3>{a.title || "Note"}</h3>
              <p>{a.body}</p>
              <p className="muted">{a.author_name} · {new Date(a.created_at).toLocaleDateString()}</p>
            </div>
          ))}
          {!hub.annotations.length && <p className="muted">No documentation yet.</p>}
        </div>
      )}

      {tab === "lineage" && lineage && (
        <div className="panel">
          <table className="registry-table">
            <thead><tr><th>Node</th><th>Type</th><th>Ref</th></tr></thead>
            <tbody>
              {lineage.nodes.map((n: any) => (
                <tr key={n.id}><td>{n.label}</td><td>{n.node_type}</td><td className="muted">{n.external_ref}</td></tr>
              ))}
            </tbody>
          </table>
          <h3>Edges</h3>
          <ul>
            {lineage.edges.map((e: any) => (
              <li key={e.id}>{e.from_node_id} —{e.edge_type}→ {e.to_node_id}</li>
            ))}
          </ul>
        </div>
      )}

      {tab === "stewardship" && (
        <table className="registry-table">
          <thead><tr><th>Role</th><th>Person</th><th>Team</th></tr></thead>
          <tbody>
            {hub.asset.stewardship.map((s: any) => (
              <tr key={s.id}><td>{s.role}</td><td>{s.person_name || "—"}</td><td>{s.team_name || "—"}</td></tr>
            ))}
          </tbody>
        </table>
      )}
    </div>
  );
}
