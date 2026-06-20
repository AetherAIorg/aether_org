"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { useParams } from "next/navigation";
import { api, assetUrl } from "@/lib/api";
import { Breadcrumbs } from "@/components/CatalogShell";

export default function TeamWorkspacePage() {
  const params = useParams();
  const slug = params.slug as string;
  const [workspace, setWorkspace] = useState<any>(null);

  useEffect(() => {
    if (!slug) return;
    api.teamBySlug(slug).then((team) => api.teamWorkspace(team.id)).then(setWorkspace).catch(console.error);
  }, [slug]);

  if (!workspace) return <p className="muted">Loading…</p>;

  return (
    <div>
      <Breadcrumbs items={[{ label: "Teams", href: "/teams" }, { label: workspace.team.name }]} />
      <header className="page-header">
        <p className="eyebrow">{workspace.team.domain}</p>
        <h1>{workspace.team.name}</h1>
        <p className="muted">{workspace.team.description}</p>
      </header>

      <div className="grid grid-2">
        <div className="panel">
          <h2 style={{ marginTop: 0 }}>Members</h2>
          <ul>
            {workspace.members.map((m: any) => (
              <li key={m.id}><Link href={`/people/${m.id}`}>{m.name}</Link> · {m.title}</li>
            ))}
          </ul>
        </div>
        <div className="panel">
          <h2 style={{ marginTop: 0 }}>Open issues</h2>
          {workspace.open_issues.slice(0, 5).map((i: any) => (
            <p key={i.id}><Link href="/issues">{i.title}</Link></p>
          ))}
        </div>
      </div>

      <div className="panel" style={{ marginTop: "1rem" }}>
        <h2 style={{ marginTop: 0 }}>Stewarded assets</h2>
        <table className="registry-table">
          <thead><tr><th>Name</th><th>Type</th><th>Certification</th></tr></thead>
          <tbody>
            {workspace.assets.map((a: any) => (
              <tr key={a.external_id}>
                <td><Link href={assetUrl(a.asset_type, a.external_id)} className="tag-name">{a.name}</Link></td>
                <td>{a.asset_type}</td>
                <td>{a.certification_level || "draft"}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
