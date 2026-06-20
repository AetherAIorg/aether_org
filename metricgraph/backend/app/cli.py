from __future__ import annotations

import argparse
import sys

from sqlalchemy import select

from app.auth import generate_api_key, hash_api_key, slugify
from app.database import SessionLocal, init_db
from app.models import ApiKey, Workspace, now_utc


def cmd_workspaces_create(args: argparse.Namespace) -> None:
    init_db()
    db = SessionLocal()
    try:
        slug = args.slug or slugify(args.name)
        existing = db.scalar(select(Workspace).where(Workspace.slug == slug).limit(1))
        if existing:
            print(f"Workspace already exists: {existing.slug} ({existing.id})")
            return
        ws = Workspace(slug=slug, name=args.name, created_at=now_utc())
        db.add(ws)
        db.commit()
        print(f"Created workspace {ws.slug} ({ws.id})")
    finally:
        db.close()


def cmd_keys_create(args: argparse.Namespace) -> None:
    init_db()
    db = SessionLocal()
    try:
        ws = db.scalar(select(Workspace).where(Workspace.slug == args.workspace).limit(1))
        if not ws:
            print(f"Workspace not found: {args.workspace}", file=sys.stderr)
            sys.exit(1)
        raw = generate_api_key(test=args.test)
        db.add(
            ApiKey(
                workspace_id=ws.id,
                key_hash=hash_api_key(raw),
                name=args.name,
                role=args.role,
                created_at=now_utc(),
            )
        )
        db.commit()
        print(f"API key ({args.role}) for workspace '{ws.slug}':")
        print(raw)
    finally:
        db.close()


def cmd_workspaces_list(_: argparse.Namespace) -> None:
    init_db()
    db = SessionLocal()
    try:
        for ws in db.scalars(select(Workspace).order_by(Workspace.created_at)):
            print(f"{ws.slug}\t{ws.name}\t{ws.id}")
    finally:
        db.close()


def main() -> None:
    parser = argparse.ArgumentParser(prog="app.cli", description="MetricGraph CLI")
    sub = parser.add_subparsers(dest="command", required=True)

    ws = sub.add_parser("workspaces")
    ws_sub = ws.add_subparsers(dest="ws_cmd", required=True)
    ws_create = ws_sub.add_parser("create")
    ws_create.add_argument("--name", required=True)
    ws_create.add_argument("--slug", default=None)
    ws_create.set_defaults(func=cmd_workspaces_create)
    ws_list = ws_sub.add_parser("list")
    ws_list.set_defaults(func=cmd_workspaces_list)

    keys = sub.add_parser("keys")
    keys_sub = keys.add_subparsers(dest="keys_cmd", required=True)
    keys_create = keys_sub.add_parser("create")
    keys_create.add_argument("--workspace", required=True, help="Workspace slug")
    keys_create.add_argument("--name", default="default")
    keys_create.add_argument("--role", default="ingest", choices=["admin", "ingest", "read"])
    keys_create.add_argument("--test", action="store_true")
    keys_create.set_defaults(func=cmd_keys_create)

    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
