"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { api } from "@/lib/api";
import { Breadcrumbs } from "@/components/CatalogShell";

export default function TeamsPage() {
  const [teams, setTeams] = useState<any[]>([]);

  useEffect(() => {
    api.teams().then(setTeams).catch(console.error);
  }, []);

  return (
    <div>
      <Breadcrumbs items={[{ label: "Teams" }]} />
      <header className="page-header">
        <p className="eyebrow">Organization</p>
        <h1>Teams</h1>
        <p className="muted">Teams own and steward catalog assets across the metric registry.</p>
      </header>
      <div className="repo-grid">
        {teams.map((t) => (
          <Link key={t.id} href={`/teams/${t.slug}`} className="repo-card">
            <h3>{t.name}</h3>
            <p className="muted">{t.domain} · {t.member_count} members</p>
            <p>{t.description || "No description"}</p>
          </Link>
        ))}
      </div>
    </div>
  );
}
