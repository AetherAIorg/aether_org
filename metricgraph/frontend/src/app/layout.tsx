import "./globals.css";
import { ClerkProvider } from "@clerk/nextjs";
import { RootProviders } from "@/components/AppShell";

export const metadata = {
  title: "Margin Registry",
  description: "Docker Hub-style registry for investment metrics",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" className="dark">
      <body className="bg-margin-bg text-white antialiased">
        <ClerkProvider>
          <RootProviders>{children}</RootProviders>
        </ClerkProvider>
      </body>
    </html>
  );
}
