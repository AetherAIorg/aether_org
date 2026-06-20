from __future__ import annotations

import hmac
from typing import Annotated

from fastapi import APIRouter, Depends, Header, HTTPException
from pydantic import BaseModel, EmailStr
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.auth import AuthContext, generate_api_key, get_auth_context, hash_api_key, require_roles, slugify
from app.config import settings
from app.database import get_db
from app.models import ApiKey, User, Workspace, WorkspaceMember, now_utc

router = APIRouter(prefix="/api/v1/auth", tags=["auth"])


class AuthSyncIn(BaseModel):
    email: EmailStr
    name: str | None = None
    image: str | None = None
    google_sub: str | None = None


class WorkspaceOut(BaseModel):
    id: str
    slug: str
    name: str
    role: str


class AuthSyncOut(BaseModel):
    user_id: str
    email: str
    name: str | None
    image: str | None
    workspace_id: str
    workspace_slug: str
    api_key: str
    workspaces: list[WorkspaceOut]


class MeOut(BaseModel):
    user_id: str
    email: str
    name: str | None
    image: str | None
    workspace_id: str
    workspace_slug: str
    workspaces: list[WorkspaceOut]


class WorkspaceSwitchIn(BaseModel):
    workspace_id: str


class WorkspaceSwitchOut(BaseModel):
    workspace_id: str
    workspace_slug: str
    api_key: str


def _verify_internal_secret(x_auth_secret: str | None) -> None:
    secret = settings.auth_secret
    if not secret:
        raise HTTPException(status_code=503, detail="AUTH_SECRET not configured")
    if not x_auth_secret or not hmac.compare_digest(secret, x_auth_secret):
        raise HTTPException(status_code=401, detail="Invalid auth secret")


def _ensure_user_workspace(db: Session, user: User) -> Workspace:
    membership = db.scalar(
        select(WorkspaceMember)
        .where(WorkspaceMember.user_id == user.id)
        .limit(1)
    )
    if membership:
        ws = db.get(Workspace, membership.workspace_id)
        if ws:
            return ws

    ws = db.scalar(select(Workspace).where(Workspace.slug == "default").limit(1))
    if not ws:
        slug = slugify(user.email.split("@")[0])
        ws = Workspace(slug=slug, name=user.name or slug)
        db.add(ws)
        db.flush()
    db.add(WorkspaceMember(user_id=user.id, workspace_id=ws.id, role="admin"))
    db.commit()
    return ws


def _mint_read_key(db: Session, workspace_id: str, user: User) -> str:
    raw = generate_api_key(test=False)
    db.add(
        ApiKey(
            workspace_id=workspace_id,
            key_hash=hash_api_key(raw),
            name=f"frontend:{user.email}",
            role="read",
            created_at=now_utc(),
        )
    )
    db.commit()
    return raw


def _user_workspaces(db: Session, user: User) -> list[WorkspaceOut]:
    rows = db.scalars(
        select(WorkspaceMember).where(WorkspaceMember.user_id == user.id)
    ).all()
    out: list[WorkspaceOut] = []
    for m in rows:
        ws = db.get(Workspace, m.workspace_id)
        if ws:
            out.append(WorkspaceOut(id=ws.id, slug=ws.slug, name=ws.name, role=m.role))
    return out


@router.post("/sync", response_model=AuthSyncOut)
def auth_sync(
    body: AuthSyncIn,
    db: Session = Depends(get_db),
    x_auth_secret: str | None = Header(default=None, alias="X-Auth-Secret"),
):
    _verify_internal_secret(x_auth_secret)
    user = db.scalar(select(User).where(User.email == body.email.lower()).limit(1))
    if not user:
        user = User(
            email=body.email.lower(),
            name=body.name,
            image=body.image,
            google_sub=body.google_sub,
        )
        db.add(user)
        db.flush()
    else:
        user.name = body.name or user.name
        user.image = body.image or user.image
        if body.google_sub:
            user.google_sub = body.google_sub
    db.commit()

    ws = _ensure_user_workspace(db, user)
    api_key = _mint_read_key(db, ws.id, user)
    return AuthSyncOut(
        user_id=user.id,
        email=user.email,
        name=user.name,
        image=user.image,
        workspace_id=ws.id,
        workspace_slug=ws.slug,
        api_key=api_key,
        workspaces=_user_workspaces(db, user),
    )


@router.get("/me", response_model=MeOut)
def auth_me(
    ctx: Annotated[AuthContext, Depends(get_auth_context)],
    db: Session = Depends(get_db),
):
    api_key = db.get(ApiKey, ctx.api_key_id)
    if not api_key or not api_key.name.startswith("frontend:"):
        raise HTTPException(status_code=403, detail="Not a user session key")
    email = api_key.name.split(":", 1)[1]
    user = db.scalar(select(User).where(User.email == email).limit(1))
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    ws = db.get(Workspace, ctx.workspace_id)
    return MeOut(
        user_id=user.id,
        email=user.email,
        name=user.name,
        image=user.image,
        workspace_id=ctx.workspace_id,
        workspace_slug=ws.slug if ws else "",
        workspaces=_user_workspaces(db, user),
    )


@router.post("/workspace/switch", response_model=WorkspaceSwitchOut)
def workspace_switch(
    body: WorkspaceSwitchIn,
    ctx: Annotated[AuthContext, Depends(get_auth_context)],
    db: Session = Depends(get_db),
):
    api_key = db.get(ApiKey, ctx.api_key_id)
    if not api_key:
        raise HTTPException(status_code=401, detail="Invalid session")
    email = api_key.name.split(":", 1)[1] if api_key.name.startswith("frontend:") else ""
    user = db.scalar(select(User).where(User.email == email).limit(1)) if email else None
    if not user:
        raise HTTPException(status_code=403, detail="User session required")

    membership = db.scalar(
        select(WorkspaceMember)
        .where(WorkspaceMember.user_id == user.id, WorkspaceMember.workspace_id == body.workspace_id)
        .limit(1)
    )
    if not membership:
        raise HTTPException(status_code=403, detail="Not a member of workspace")

    ws = db.get(Workspace, body.workspace_id)
    if not ws:
        raise HTTPException(status_code=404, detail="Workspace not found")
    new_key = _mint_read_key(db, ws.id, user)
    return WorkspaceSwitchOut(workspace_id=ws.id, workspace_slug=ws.slug, api_key=new_key)
