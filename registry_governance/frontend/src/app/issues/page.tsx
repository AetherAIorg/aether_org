"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { api } from "@/lib/api";
import { Breadcrumbs } from "@/components/CatalogShell";

export default function IssuesPage() {
  const [issues, setIssues] = useState<any[]>([]);
  const [people, setPeople] = useState<any[]>([]);

  useEffect(() => {
    Promise.all([api.issues(), api.people()]).then(([i, p]) => {
      setIssues(i);
      setPeople(p);
    }).catch(console.error);
  }, []);

  async function assign(issueId: string, assigneeId: string) {
    await api.patchIssue(issueId, { assignee_id: assigneeId, status: "in_progress" });
    setIssues(await api.issues());
  }

  return (
    <div>
      <Breadcrumbs items={[{ label: "Issues" }]} />
      <header className="page-header">
        <p className="eyebrow">Governance</p>
        <h1>Issue inbox</h1>
        <p className="muted">Discovery issues from the registry with assignee and status tracking.</p>
      </header>

      <table className="registry-table">
        <thead>
          <tr>
            <th>Severity</th>
            <th>Title</th>
            <th>Status</th>
            <th>Assignee</th>
            <th>Action</th>
          </tr>
        </thead>
        <tbody>
          {issues.map((issue) => (
            <tr key={issue.id}>
              <td><span className={`pill ${issue.severity === "high" ? "pill-danger" : "pill-warning"}`}>{issue.severity}</span></td>
              <td>{issue.title}</td>
              <td>{issue.status}</td>
              <td>{issue.assignee_name || "—"}</td>
              <td>
                <select
                  defaultValue={issue.assignee_id || ""}
                  onChange={(e) => e.target.value && void assign(issue.id, e.target.value)}
                >
                  <option value="">Assign…</option>
                  {people.map((p) => (
                    <option key={p.id} value={p.id}>{p.name}</option>
                  ))}
                </select>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
      {!issues.length && <p className="muted">No issues synced yet.</p>}
    </div>
  );
}
