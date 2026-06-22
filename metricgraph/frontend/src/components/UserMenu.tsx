"use client";

import { useClerk, useUser } from "@clerk/nextjs";
import { useWorkspaceSlug } from "@/components/ApiKeyProvider";

export function UserMenu() {
  const { user } = useUser();
  const { signOut } = useClerk();
  const workspaceSlug = useWorkspaceSlug();

  if (!user) return null;

  const name = user.fullName || user.primaryEmailAddress?.emailAddress || "User";
  const image = user.imageUrl;

  return (
    <div className="sidebar-user">
      {image ? (
        // eslint-disable-next-line @next/next/no-img-element
        <img src={image} alt="" className="sidebar-avatar" />
      ) : (
        <div className="sidebar-avatar sidebar-avatar-fallback">
          {name[0]?.toUpperCase() || "?"}
        </div>
      )}
      <div className="sidebar-user-meta">
        <strong>{name}</strong>
        <span>{workspaceSlug || "workspace"}</span>
      </div>
      <button
        type="button"
        className="sidebar-signout"
        onClick={() => signOut({ redirectUrl: "/sign-in" })}
      >
        Sign out
      </button>
    </div>
  );
}
