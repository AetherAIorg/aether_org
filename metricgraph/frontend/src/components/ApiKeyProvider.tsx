"use client";

import { createContext, useContext, useEffect, useState } from "react";
import { useAuth, useUser } from "@clerk/nextjs";

type ApiKeyContextValue = {
  apiKey?: string;
  workspaceSlug?: string;
  loading: boolean;
};

const ApiKeyContext = createContext<ApiKeyContextValue>({ loading: true });

export function ApiKeyProvider({ children }: { children: React.ReactNode }) {
  const { isLoaded, isSignedIn } = useAuth();
  const { user } = useUser();
  const [apiKey, setApiKey] = useState<string>();
  const [workspaceSlug, setWorkspaceSlug] = useState<string>();
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (!isLoaded) return;

    if (!isSignedIn) {
      setApiKey(undefined);
      setWorkspaceSlug(undefined);
      setLoading(false);
      return;
    }

    setLoading(true);
    fetch("/api/auth/sync-backend")
      .then((res) => (res.ok ? res.json() : Promise.reject(res)))
      .then((data) => {
        setApiKey(data.api_key);
        setWorkspaceSlug(data.workspace_slug);
      })
      .catch(() => {
        setApiKey(undefined);
        setWorkspaceSlug(undefined);
      })
      .finally(() => setLoading(false));
  }, [isLoaded, isSignedIn, user?.id]);

  return (
    <ApiKeyContext.Provider value={{ apiKey, workspaceSlug, loading }}>
      {children}
    </ApiKeyContext.Provider>
  );
}

export function useApiKey(): string | undefined {
  return useContext(ApiKeyContext).apiKey;
}

export function useWorkspaceSlug(): string | undefined {
  return useContext(ApiKeyContext).workspaceSlug;
}

export function useApiKeyLoading(): boolean {
  return useContext(ApiKeyContext).loading;
}
