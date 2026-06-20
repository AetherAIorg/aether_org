"use client";

import { useEffect, useState } from "react";
import { useApiKey, v1Api, type QueryEvent } from "@/lib/api-v1";

const CHANNELS = ["", "linear", "slack", "teams", "web"];
const INTENTS = ["", "context", "definition", "impact", "stewardship", "conflicts", "search"];

export default function ActivityPage() {
  const apiKey = useApiKey();
  const [items, setItems] = useState<QueryEvent[]>([]);
  const [channel, setChannel] = useState("");
  const [intent, setIntent] = useState("");
  const [selected, setSelected] = useState<(QueryEvent & { answer_full?: string | null }) | null>(null);

  useEffect(() => {
    if (!apiKey) return;
    v1Api.activityQueries(apiKey, { channel: channel || undefined, intent: intent || undefined }).then(
      (r) => setItems(r.items)
    );
  }, [apiKey, channel, intent]);

  async function openDetail(id: string) {
    if (!apiKey) return;
    const detail = await v1Api.activityQuery(apiKey, id);
    setSelected(detail);
  }

  return (
    <div>
      <div className="page-header">
        <h1>Activity</h1>
        <p className="page-subtitle">Queries from Linear, Slack, Teams, and the web</p>
      </div>
      <div className="filter-row">
        <select value={channel} onChange={(e) => setChannel(e.target.value)} className="filter-select">
          {CHANNELS.map((c) => (
            <option key={c || "all"} value={c}>
              {c || "All channels"}
            </option>
          ))}
        </select>
        <select value={intent} onChange={(e) => setIntent(e.target.value)} className="filter-select">
          {INTENTS.map((i) => (
            <option key={i || "all"} value={i}>
              {i || "All intents"}
            </option>
          ))}
        </select>
      </div>
      <div className="activity-list">
        {items.map((item) => (
          <button
            key={item.id}
            type="button"
            className="activity-card"
            onClick={() => openDetail(item.id)}
          >
            <div className="activity-card-head">
              <span className={`pill pill-${item.channel}`}>{item.channel}</span>
              <span className="pill pill-muted">{item.intent}</span>
              <time>{new Date(item.created_at).toLocaleString()}</time>
            </div>
            <strong>{item.query_text}</strong>
            <p>{item.answer_preview}</p>
          </button>
        ))}
        {!items.length && <p className="text-margin-muted">No queries logged yet.</p>}
      </div>
      {selected && (
        <div className="activity-drawer">
          <button type="button" className="drawer-close" onClick={() => setSelected(null)}>
            Close
          </button>
          <h2>{selected.query_text}</h2>
          <div className="drawer-meta">
            <span className="pill">{selected.channel}</span>
            <span className="pill pill-muted">{selected.intent}</span>
          </div>
          {selected.external_url && (
            <a href={selected.external_url} target="_blank" rel="noreferrer" className="drawer-link">
              Open in Linear
            </a>
          )}
          <pre className="drawer-answer">{selected.answer_full || selected.answer_preview}</pre>
        </div>
      )}
    </div>
  );
}
