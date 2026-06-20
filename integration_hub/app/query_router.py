from __future__ import annotations

import re

from app import formatting


def _clean_term(term: str) -> str:
    return term.strip().strip("?.!").strip(" `\"'").strip()


def parse_query(text: str, mention_tokens: list[str] | None = None) -> tuple[str, str] | None:
    """Detect metric/context questions. Returns (intent, query) or None."""
    if not text:
        return None
    low = text.lower()
    tokens = mention_tokens or ["@margin", "@metricgraph"]

    m = re.search(r"/margin\s+search\s+(.+)", low, re.DOTALL)
    if m:
        return "search", _clean_term(text[m.start(1):])

    m = re.search(r"/metric\s+search\s+(.+)", low, re.DOTALL)
    if m:
        return "search", _clean_term(text[m.start(1):])

    m = re.search(r"context:\s*(.+)", low, re.DOTALL)
    if m:
        return "context", _clean_term(text[m.start(1):])

    m = re.search(r"who owns\s+(.+)", low, re.DOTALL)
    if m:
        return "stewardship", _clean_term(m.group(1))

    m = re.search(r"what uses\s+(.+)", low, re.DOTALL)
    if m:
        return "impact", _clean_term(m.group(1))

    m = re.search(r"why is\s+(.+?)\s+conflicting", low, re.DOTALL)
    if m:
        return "conflicts", _clean_term(m.group(1))

    m = re.search(r"/margin\s+(.+)", low, re.DOTALL)
    if m:
        return "definition", _clean_term(text[m.start(1):])

    m = re.search(r"/metric\s+(.+)", low, re.DOTALL)
    if m:
        return "definition", _clean_term(text[m.start(1):])

    m = re.search(r"metric:\s*(.+)", low, re.DOTALL)
    if m:
        return "definition", _clean_term(text[m.start(1):])

    for token in tokens:
        if token.lower() in low:
            cleaned = re.sub(re.escape(token), "", text, flags=re.IGNORECASE).strip()
            m = re.search(
                r"(?:what\s+is|what's|define|definition\s+of|tell me about|lookup|look up|context for)\s+(.+)",
                cleaned,
                re.IGNORECASE | re.DOTALL,
            )
            if m:
                q = _clean_term(m.group(1))
                if "context" in cleaned.lower()[:20]:
                    return "context", q
                return "definition", q
            if cleaned:
                return "definition", _clean_term(cleaned)
    return None
