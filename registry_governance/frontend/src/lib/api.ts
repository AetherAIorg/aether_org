const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8090";
const REGISTRY_URL = process.env.NEXT_PUBLIC_REGISTRY_URL || "http://localhost:3000";

function headers(actorEmail?: string): HeadersInit {
  const h: HeadersInit = { "Content-Type": "application/json" };
  if (actorEmail) h["X-Actor-Email"] = actorEmail;
  return h;
}

async function request<T>(path: string, options?: RequestInit): Promise<T> {
  const res = await fetch(`${API_URL}${path}`, options);
  if (!res.ok) throw new Error(await res.text());
  return res.json();
}

export const api = {
  registryUrl: REGISTRY_URL,
  health: () => request<{ status: string }>("/api/health"),
  catalog: (params?: Record<string, string>) => {
    const q = new URLSearchParams(params).toString();
    return request<any[]>(`/api/catalog${q ? `?${q}` : ""}`);
  },
  teams: () => request<any[]>("/api/teams"),
  teamBySlug: (slug: string) => request<any>(`/api/teams/by-slug/${slug}`),
  teamWorkspace: (id: string) => request<any>(`/api/teams/${id}/workspace`),
  people: () => request<any[]>("/api/people"),
  person: (id: string) => request<any[]>(`/api/people`).then((p) => p.find((x) => x.id === id)),
  asset: (type: string, id: string) => request<any>(`/api/assets/${type}/${id}`),
  lineage: (type: string, id: string) => request<any>(`/api/lineage/${type}/${id}`),
  issues: (status?: string) =>
    request<any[]>(`/api/issues${status ? `?status=${status}` : ""}`),
  patchIssue: (id: string, body: object) =>
    request<any>(`/api/issues/${id}`, { method: "PATCH", headers: headers(), body: JSON.stringify(body) }),
  sync: () => request<any>("/api/sync/metricgraph", { method: "POST" }),
  addAnnotation: (body: object, actorEmail?: string) =>
    request<any>("/api/annotations", {
      method: "POST",
      headers: headers(actorEmail),
      body: JSON.stringify(body),
    }),
};

export function assetUrl(type: string, id: string) {
  return `/assets/${type}/${id}`;
}
