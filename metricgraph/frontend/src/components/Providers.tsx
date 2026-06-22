"use client";

import { ApiKeyProvider } from "@/components/ApiKeyProvider";

export function Providers({ children }: { children: React.ReactNode }) {
  return <ApiKeyProvider>{children}</ApiKeyProvider>;
}
