"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { ReactNode, useState } from "react";

export function CatalogShell({ children }: { children: ReactNode }) {
  const router = useRouter();
  const [q, setQ] = useState("");

  function handleSearch(e: React.FormEvent) {
    e.preventDefault();
    if (q.trim()) router.push(`/?q=${encodeURIComponent(q.trim())}`);
  }

  return (
    <div className="registry-shell">
      <header className="registry-topbar">
        <form className="registry-topbar-search" onSubmit={handleSearch}>
          <input
            placeholder="Search catalog assets, teams, documentation…"
            value={q}
            onChange={(e) => setQ(e.target.value)}
          />
        </form>
      </header>
      <div className="registry-content">{children}</div>
    </div>
  );
}

export function Breadcrumbs({ items }: { items: { label: string; href?: string }[] }) {
  return (
    <nav className="breadcrumbs" style={{ marginBottom: "1rem" }}>
      {items.map((item, i) => (
        <span key={i} style={{ display: "contents" }}>
          {i > 0 && <span className="breadcrumbs-sep">/</span>}
          {item.href ? <Link href={item.href}>{item.label}</Link> : <span>{item.label}</span>}
        </span>
      ))}
    </nav>
  );
}
