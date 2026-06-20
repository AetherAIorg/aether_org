import { Suspense } from "react";
import HomePageClient from "./HomePageClient";

export default function HomePage() {
  return (
    <Suspense fallback={<p className="muted">Loading…</p>}>
      <HomePageClient />
    </Suspense>
  );
}
