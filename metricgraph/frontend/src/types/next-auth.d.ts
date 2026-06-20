import "next-auth";

declare module "next-auth" {
  interface Session {
    apiKey?: string;
    workspaceId?: string;
    workspaceSlug?: string;
    workspaces?: Array<{ id: string; slug: string; name: string; role: string }>;
  }
}

declare module "next-auth/jwt" {
  interface JWT {
    apiKey?: string;
    workspaceId?: string;
    workspaceSlug?: string;
    workspaces?: Array<{ id: string; slug: string; name: string; role: string }>;
  }
}
