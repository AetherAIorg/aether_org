import type { NextAuthOptions } from "next-auth";
import GoogleProvider from "next-auth/providers/google";
import EmailProvider from "next-auth/providers/email";

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

async function syncWithBackend(profile: {
  email: string;
  name?: string | null;
  image?: string | null;
  sub?: string;
}) {
  const res = await fetch(`${API_URL}/api/v1/auth/sync`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      "X-Auth-Secret": process.env.AUTH_SECRET || "",
    },
    body: JSON.stringify({
      email: profile.email,
      name: profile.name,
      image: profile.image,
      google_sub: profile.sub,
    }),
  });
  if (!res.ok) {
    throw new Error(`Auth sync failed: ${await res.text()}`);
  }
  return res.json();
}

export const authOptions: NextAuthOptions = {
  providers: [
    GoogleProvider({
      clientId: process.env.AUTH_GOOGLE_ID || "",
      clientSecret: process.env.AUTH_GOOGLE_SECRET || "",
    }),
    ...(process.env.AUTH_RESEND_KEY
      ? [
          EmailProvider({
            server: {
              host: "smtp.resend.com",
              port: 465,
              auth: { user: "resend", pass: process.env.AUTH_RESEND_KEY },
            },
            from: process.env.AUTH_EMAIL_FROM || "Margin <onboarding@resend.dev>",
          }),
        ]
      : []),
  ],
  pages: { signIn: "/login" },
  session: { strategy: "jwt" },
  callbacks: {
    async jwt({ token, user, account, profile }) {
      if (user?.email && (account || profile)) {
        try {
          const synced = await syncWithBackend({
            email: user.email,
            name: user.name,
            image: user.image,
            sub: account?.providerAccountId,
          });
          token.apiKey = synced.api_key;
          token.workspaceId = synced.workspace_id;
          token.workspaceSlug = synced.workspace_slug;
          token.workspaces = synced.workspaces;
        } catch {
          // Allow local dev without backend sync
        }
      }
      return token;
    },
    async session({ session, token }) {
      if (session.user) {
        (session as any).apiKey = token.apiKey;
        (session as any).workspaceId = token.workspaceId;
        (session as any).workspaceSlug = token.workspaceSlug;
        (session as any).workspaces = token.workspaces;
      }
      return session;
    },
  },
  secret: process.env.AUTH_SECRET || "placeholder-until-configured",
};
