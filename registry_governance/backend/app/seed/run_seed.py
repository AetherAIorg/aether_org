from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import select

from app.database import SessionLocal
from app.models import (
    Annotation,
    AssetMirror,
    Certification,
    Person,
    Stewardship,
    Team,
    TeamMembership,
)


def run_seed() -> None:
    db = SessionLocal()
    try:
        if db.scalar(select(Team).limit(1)):
            return

        teams = [
            Team(slug="investment-operations", name="Investment Operations", domain="Operations"),
            Team(slug="investment-analytics", name="Investment Analytics", domain="Analytics"),
            Team(slug="fund-accounting", name="Fund Accounting", domain="Accounting"),
        ]
        for t in teams:
            db.add(t)
        db.flush()

        people_data = [
            ("alex.chen@margin.local", "Alex Chen", "Ops Lead", teams[0].id, "lead"),
            ("jordan.lee@margin.local", "Jordan Lee", "Analytics Lead", teams[1].id, "lead"),
            ("sam.patel@margin.local", "Sam Patel", "Fund Accountant", teams[2].id, "lead"),
            ("riley.kim@margin.local", "Riley Kim", "Performance Analyst", teams[1].id, "member"),
            ("taylor.ng@margin.local", "Taylor Ng", "Ops Analyst", teams[0].id, "member"),
            ("casey.rodriguez@margin.local", "Casey Rodriguez", "Controller", teams[2].id, "member"),
        ]
        people: list[Person] = []
        for email, name, title, team_id, role in people_data:
            p = Person(email=email, name=name, title=title)
            db.add(p)
            db.flush()
            db.add(TeamMembership(person_id=p.id, team_id=team_id, role=role))
            people.append(p)

        metric = db.scalar(
            select(AssetMirror).where(
                AssetMirror.asset_type == "metric",
                AssetMirror.name.ilike("%Fund-Level Net IRR%"),
            )
        )
        if metric:
            db.add(
                Stewardship(
                    asset_type="metric",
                    asset_external_id=metric.external_id,
                    role="owner",
                    team_id=teams[0].id,
                )
            )
            db.add(
                Stewardship(
                    asset_type="metric",
                    asset_external_id=metric.external_id,
                    role="steward",
                    team_id=teams[1].id,
                )
            )
            db.add(
                Stewardship(
                    asset_type="metric",
                    asset_external_id=metric.external_id,
                    role="expert",
                    person_id=people[3].id,
                )
            )
            db.add(
                Certification(
                    asset_type="metric",
                    asset_external_id=metric.external_id,
                    level="certified",
                    certified_by_id=people[0].id,
                    certified_at=datetime.now(timezone.utc),
                    notes="Approved for fund reporting",
                )
            )
            db.add(
                Annotation(
                    asset_type="metric",
                    asset_external_id=metric.external_id,
                    author_id=people[1].id,
                    kind="faq",
                    title="When to use Net IRR vs Gross IRR",
                    body="Use this certified Net IRR metric when fees and expenses must be reflected in the return.",
                )
            )
            db.add(
                Annotation(
                    asset_type="metric",
                    asset_external_id=metric.external_id,
                    author_id=people[0].id,
                    kind="usage",
                    title="Required datasets",
                    body="Upload fund_cashflows.csv and optionally fund_nav.csv before running Pull & run.",
                )
            )

        candidate = db.scalar(select(AssetMirror).where(AssetMirror.asset_type == "candidate").limit(1))
        if candidate:
            db.add(
                Certification(
                    asset_type="candidate",
                    asset_external_id=candidate.external_id,
                    level="reviewed",
                    certified_by_id=people[1].id,
                    certified_at=datetime.now(timezone.utc),
                )
            )

        db.commit()
    finally:
        db.close()


if __name__ == "__main__":
    run_seed()
