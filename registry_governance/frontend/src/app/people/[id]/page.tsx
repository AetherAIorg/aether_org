"use client";

import { useEffect, useState } from "react";
import { useParams } from "next/navigation";
import { api } from "@/lib/api";
import { Breadcrumbs } from "@/components/CatalogShell";

export default function PersonPage() {
  const params = useParams();
  const id = params.id as string;
  const [person, setPerson] = useState<any>(null);

  useEffect(() => {
    if (!id) return;
    api.people().then((people) => setPerson(people.find((p) => p.id === id))).catch(console.error);
  }, [id]);

  if (!person) return <p className="muted">Loading…</p>;

  return (
    <div>
      <Breadcrumbs items={[{ label: "People" }, { label: person.name }]} />
      <header className="page-header">
        <p className="eyebrow">Person</p>
        <h1>{person.name}</h1>
        <p className="muted">{person.title} · {person.email}</p>
      </header>
    </div>
  );
}
