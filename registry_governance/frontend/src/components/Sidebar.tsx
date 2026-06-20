"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

const links = [
  { href: "/", label: "Catalog" },
  { href: "/teams", label: "Teams" },
  { href: "/issues", label: "Issues" },
];

export function Sidebar() {
  const pathname = usePathname();
  const registryUrl = process.env.NEXT_PUBLIC_REGISTRY_URL || "http://localhost:3000";

  return (
    <aside className="sidebar">
      <div className="brand">
        <strong>Margin Catalog</strong>
        <span>Data governance</span>
      </div>
      <div className="nav-group">
        <div className="nav-group-label">Governance</div>
        <nav>
          {links.map((l) => (
            <Link
              key={l.href}
              href={l.href}
              className={pathname === l.href || (l.href !== "/" && pathname.startsWith(l.href)) ? "active" : ""}
            >
              {l.label}
            </Link>
          ))}
        </nav>
      </div>
      <div className="nav-group">
        <div className="nav-group-label">Registry</div>
        <nav>
          <a href={`${registryUrl}/metrics`} target="_blank" rel="noreferrer">
            Open Registry
          </a>
        </nav>
      </div>
    </aside>
  );
}
