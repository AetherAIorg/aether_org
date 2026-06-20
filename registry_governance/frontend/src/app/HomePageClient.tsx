"use client";

import { useEffect, useState } from "react";
import { useSearchParams } from "next/navigation";
import Link from "next/link";
import { api, assetUrl } from "@/lib/api";

function certClass(level: string | null | undefined) {
  if (level === "certified") return "pill-success";
  if (level === "reviewed") return "pill-warning";
  return "pill-muted";
}

export default function HomePageClient() {
  const searchParams = useSearchParams();
  const [items, setItems] = useState<any[]>([]);
  const [syncing, setSyncing] = useState(false);
  const q = searchParams.get("q") || "";
  const cert = searchParams.get("certification") || "";

  useEffect(() => {
    const params: Record<string, string> = {};
    if (q) params.q = q;
    if (cert) params.certification = cert;
    api.catalog(Object.keys(params).length ? params : undefined).then(setItems).catch(console.error);
  }, [q, cert]);

  async function sync() {
    setSyncing(true);
    try {
      await api.sync();
      const params: Record<string, string> = {};
      if (q) params.q = q;
      if (cert) params.certification = cert;
      setItems(await api.catalog(Object.keys(params).length ? params : undefined));
    } finally {
      setSyncing(false);
    }
  }

  return (
    <div>
      <header className="page-header">
        <p className="eyebrow">Margin Catalog</p>
        <h1>Data governance catalog</h1>
        <p className="muted">Teams, stewardship, documentation, certification, and lineage for registry assets.</p>
        <div className="page-header-actions">
          <button type="button" className="btn btn-secondary" onClick={() => void sync()} disabled={syncing}>
            {syncing ? "Syncing…" : "Sync from Registry"}
          </button>
        </div>
      </header>

      <div className="filter-bar">
        <Link href="/?certification=certified" className={`pill ${cert === "certified" ? "pill-success" : "pill-muted"}`}>Certified</Link>
        <Link href="/?certification=reviewed" className={`pill ${cert === "reviewed" ? "pill-warning" : "pill-muted"}`}>Reviewed</Link>
        <Link href="/" className="pill pill-muted">All</Link>
      </div>

      <table className="registry-table">
        <thead>
          <tr>
            <th>Name</th>
            <th>Type</th>
            <th>Domain</th>
            <th>Certification</th>
            <th>Owner</th>
          </tr>
        </thead>
        <tbody>
          {items.map((item) => (
            <tr key={`${item.asset_type}-${item.external_id}`}>
              <td>
                <Link href={assetUrl(item.asset_type, item.external_id)} className="tag-name">{item.name}</Link>
              </td>
              <td><span className="pill">{item.asset_type}</span></td>
              <td className="muted">{item.domain || "—"}</td>
              <td><span className={`pill ${certClass(item.certification_level)}`}>{item.certification_level || "draft"}</span></td>
              <td className="muted">{item.owner_label || "—"}</td>
            </tr>
          ))}
        </tbody>
      </table>
      {!items.length && <p className="muted">No assets yet. Start MetricGraph and sync.</p>}
    </div>
  );
}
