"use client";

import { useApiKey } from "@/components/ApiKeyProvider";

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export { useApiKey };

export async function v1Request<T>(
  path: string,
  apiKey: string | undefined,
  options?: RequestInit,
): Promise<T> {
  if (!apiKey) throw new Error("Not authenticated");
  const res = await fetch(`${API_URL}${path}`, {
    ...options,
    headers: {
      Authorization: `Bearer ${apiKey}`,
      "Content-Type": "application/json",
      ...(options?.headers || {}),
    },
  });
  if (!res.ok) throw new Error(await res.text());
  return res.json();
}

export type GraphNode = {
  id: string;
  node_type: string;
  label: string;
  external_ref: string;
  properties?: Record<string, unknown>;
};

export type GraphEdge = {
  id: string;
  from_node_id: string;
  to_node_id: string;
  edge_type: string;
  source?: string;
};

export type QueryEvent = {
  id: string;
  channel: string;
  intent: string;
  query_text: string;
  answer_preview: string;
  external_ref: string | null;
  external_url: string | null;
  author: string | null;
  metric_id: string | null;
  graph_node_count: number;
  created_at: string;
};

export const v1Api = {
  graphStats: (apiKey: string) => v1Request<{ nodes: number; edges: number }>("/api/v1/graph/stats", apiKey),
  graphContext: (apiKey: string, metricId: string, depth = 2) =>
    v1Request<{ nodes: GraphNode[]; edges: GraphEdge[] }>(
      `/api/v1/graph/context/${metricId}?depth=${depth}`,
      apiKey,
    ),
  activityQueries: (apiKey: string, params?: { channel?: string; intent?: string }) => {
    const q = new URLSearchParams();
    if (params?.channel) q.set("channel", params.channel);
    if (params?.intent) q.set("intent", params.intent);
    return v1Request<{ total: number; items: QueryEvent[] }>(
      `/api/v1/activity/queries?${q.toString()}`,
      apiKey,
    );
  },
  activityQuery: (apiKey: string, id: string) =>
    v1Request<QueryEvent & { answer_full: string | null }>(`/api/v1/activity/queries/${id}`, apiKey),
};
