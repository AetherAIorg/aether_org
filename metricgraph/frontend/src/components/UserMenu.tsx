"use client";

import { signOut, useSession } from "next-auth/react";

export function UserMenu() {
  const { data: session } = useSession();
  const user = session?.user;
  if (!user) return null;

  return (
    <div className="sidebar-user">
      {user.image ? (
        // eslint-disable-next-line @next/next/no-img-element
        <img src={user.image} alt="" className="sidebar-avatar" />
      ) : (
        <div className="sidebar-avatar sidebar-avatar-fallback">
          {(user.name || user.email || "?")[0].toUpperCase()}
        </div>
      )}
      <div className="sidebar-user-meta">
        <strong>{user.name || user.email}</strong>
        <span>{(session as any).workspaceSlug || "workspace"}</span>
      </div>
      <button type="button" className="sidebar-signout" onClick={() => signOut({ callbackUrl: "/login" })}>
        Sign out
      </button>
    </div>
  );
}
