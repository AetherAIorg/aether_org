from __future__ import annotations

import hashlib
import secrets
from dataclasses import dataclass
from typing import Annotated

from fastapi import Depends, HTTPException, Request
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import ApiKey, now_utc


KEY_PREFIX_LIVE = "mg_live_"
KEY_PREFIX_TEST = "mg_test_"


def hash_api_key(raw_key: str) -> str:
    return hashlib.sha256(raw_key.encode("utf-8")).hexdigest()


def generate_api_key(*, test: bool = False) -> str:
    prefix = KEY_PREFIX_TEST if test else KEY_PREFIX_LIVE
    return f"{prefix}{secrets.token_urlsafe(32)}"


def slugify(name: str) -> str:
    slug = "".join(ch.lower() if ch.isalnum() else "-" for ch in name.strip())
    while "--" in slug:
        slug = slug.replace("--", "-")
    return slug.strip("-") or "workspace"


@dataclass
class AuthContext:
    workspace_id: str
    api_key_id: str
    role: str


def _resolve_auth(authorization: str | None, db: Session) -> AuthContext:
    if not authorization or not authorization.lower().startswith("bearer "):
        raise HTTPException(status_code=401, detail="Missing or invalid Authorization header")
    raw = authorization.split(" ", 1)[1].strip()
    if not raw:
        raise HTTPException(status_code=401, detail="Empty API key")
    key_hash = hash_api_key(raw)
    api_key = db.scalar(select(ApiKey).where(ApiKey.key_hash == key_hash).limit(1))
    if not api_key:
        raise HTTPException(status_code=401, detail="Invalid API key")
    api_key.last_used_at = now_utc()
    db.commit()
    return AuthContext(workspace_id=api_key.workspace_id, api_key_id=api_key.id, role=api_key.role)


def get_auth_context(request: Request, db: Session = Depends(get_db)) -> AuthContext:
    auth = request.headers.get("Authorization")
    ctx = _resolve_auth(auth, db)
    request.state.workspace_id = ctx.workspace_id
    request.state.api_key_id = ctx.api_key_id
    request.state.auth_role = ctx.role
    return ctx


def require_roles(*roles: str):
    def _dep(ctx: Annotated[AuthContext, Depends(get_auth_context)]) -> AuthContext:
        if ctx.role == "admin":
            return ctx
        if ctx.role not in roles:
            raise HTTPException(status_code=403, detail=f"Role '{ctx.role}' cannot perform this action")
        return ctx

    return _dep
