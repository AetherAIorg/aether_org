import "./globals.css";
import { CatalogShell } from "@/components/CatalogShell";
import { Sidebar } from "@/components/Sidebar";

export const metadata = {
  title: "Margin Catalog",
  description: "Data governance for investment metrics",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body>
        <div className="app-shell">
          <Sidebar />
          <CatalogShell>{children}</CatalogShell>
        </div>
      </body>
    </html>
  );
}
