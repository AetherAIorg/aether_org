from __future__ import annotations

import re
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.metricgraph_client import MetricGraphClient
from app.models import ActivityLog, AssetMirror, IssueMirror, Person, Stewardship, Team, now_utc


def _slugify(text: str) -> str:
    s = re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")
    return s or "team"


def _ensure_person_for_label(db: Session, label: str) -> Person:
    email = f"{_slugify(label)}@margin.local"
    person = db.scalar(select(Person).where(Person.email == email))
    if person:
        return person
    person = Person(email=email, name=label, title="Imported owner")
    db.add(person)
    db.flush()
    return person


def _ensure_team_for_label(db: Session, label: str) -> Team:
    slug = _slugify(label)
    team = db.scalar(select(Team).where(Team.slug == slug))
    if team:
        return team
    team = Team(slug=slug, name=label, domain=label)
    db.add(team)
    db.flush()
    return team


def _upsert_asset(
    db: Session,
    asset_type: str,
    external_id: str,
    name: str,
    summary: str | None,
    domain: str | None,
    owner_label: str | None,
    payload: dict,
) -> AssetMirror:
    row = db.scalar(
        select(AssetMirror).where(
            AssetMirror.asset_type == asset_type,
            AssetMirror.external_id == external_id,
        )
    )
    if row:
        row.name = name
        row.summary = summary
        row.domain = domain
        row.owner_label = owner_label
        row.mg_payload = payload
        row.synced_at = now_utc()
        return row
    row = AssetMirror(
        asset_type=asset_type,
        external_id=external_id,
        name=name,
        summary=summary,
        domain=domain,
        owner_label=owner_label,
        mg_payload=payload,
    )
    db.add(row)
    db.flush()
    return row


def _seed_stewardship_from_owner(
    db: Session, asset_type: str, external_id: str, owner_label: str | None
) -> int:
    if not owner_label:
        return 0
    existing = db.scalar(
        select(Stewardship).where(
            Stewardship.asset_type == asset_type,
            Stewardship.asset_external_id == external_id,
            Stewardship.role == "owner",
        )
    )
    if existing:
        return 0
    team = _ensure_team_for_label(db, owner_label)
    db.add(
        Stewardship(
            asset_type=asset_type,
            asset_external_id=external_id,
            role="owner",
            team_id=team.id,
        )
    )
    return 1


def sync_from_metricgraph(db: Session, client: MetricGraphClient) -> dict[str, int]:
    counts = {"metrics": 0, "artifacts": 0, "functions": 0, "candidates": 0, "issues": 0, "stewardship_seeded": 0}

    for metric in client.list_metrics():
        tags = client.list_metric_tags(metric["id"])
        payload = {**metric, "tags": tags}
        _upsert_asset(
            db,
            "metric",
            metric["id"],
            metric.get("canonical_name", metric["id"]),
            metric.get("description"),
            metric.get("domain"),
            metric.get("owner"),
            payload,
        )
        counts["metrics"] += 1
        counts["stewardship_seeded"] += _seed_stewardship_from_owner(
            db, "metric", metric["id"], metric.get("owner")
        )

    for artifact in client.list_artifacts():
        _upsert_asset(
            db,
            "artifact",
            artifact["id"],
            artifact.get("filename", artifact["id"]),
            f"{artifact.get('artifact_type', '')} source file",
            None,
            artifact.get("owner"),
            artifact,
        )
        counts["artifacts"] += 1
        counts["stewardship_seeded"] += _seed_stewardship_from_owner(
            db, "artifact", artifact["id"], artifact.get("owner")
        )

    for fn in client.list_functions():
        _upsert_asset(
            db,
            "function",
            fn["id"],
            fn.get("name", fn["id"]),
            fn.get("description"),
            None,
            fn.get("owner"),
            fn,
        )
        counts["functions"] += 1
        counts["stewardship_seeded"] += _seed_stewardship_from_owner(
            db, "function", fn["id"], fn.get("owner")
        )

    for candidate in client.list_candidates():
        detail = client.get_candidate(candidate["id"])
        _upsert_asset(
            db,
            "candidate",
            candidate["id"],
            candidate.get("display_name", candidate["id"]),
            f"{candidate.get('family', '')} candidate",
            candidate.get("family"),
            None,
            detail,
        )
        counts["candidates"] += 1

    for issue in client.list_issues():
        key = f"{issue.get('issue_type')}:{issue.get('title', '')}"
        row = db.scalar(select(IssueMirror).where(IssueMirror.external_key == key))
        if row:
            row.issue_type = issue.get("issue_type", "")
            row.title = issue.get("title", "")
            row.explanation = issue.get("explanation", "")
            row.severity = issue.get("severity", "medium")
            row.mg_payload = issue
            row.synced_at = now_utc()
        else:
            db.add(
                IssueMirror(
                    external_key=key,
                    issue_type=issue.get("issue_type", ""),
                    title=issue.get("title", ""),
                    explanation=issue.get("explanation", ""),
                    severity=issue.get("severity", "medium"),
                    mg_payload=issue,
                )
            )
        counts["issues"] += 1

    db.add(
        ActivityLog(
            event_type="sync.completed",
            summary="MetricGraph sync completed",
            payload=counts,
        )
    )
    db.commit()
    return counts
