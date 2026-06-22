"use client";

import { usePathname } from "next/navigation";
import { Providers } from "@/components/Providers";
import { RegistryShell } from "@/components/RegistryShell";
import { Sidebar } from "@/components/Sidebar";

export function AppShell({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();
  if (pathname.startsWith("/login") || pathname.startsWith("/sign-in") || pathname.startsWith("/sign-up")) {
    return <>{children}</>;
  }
  return (
    <div className="app-shell">
      <Sidebar />
      <RegistryShell>{children}</RegistryShell>
    </div>
  );
}

export function RootProviders({ children }: { children: React.ReactNode }) {
  return (
    <Providers>
      <AppShell>{children}</AppShell>
    </Providers>
  );
}
