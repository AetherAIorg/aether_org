import { currentUser } from "@clerk/nextjs/server";
import { NextResponse } from "next/server";

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export async function GET() {
  const user = await currentUser();
  if (!user) {
    return NextResponse.json({ error: "Unauthorized" }, { status: 401 });
  }

  const email = user.emailAddresses[0]?.emailAddress;
  if (!email) {
    return NextResponse.json({ error: "No email on account" }, { status: 400 });
  }

  const googleAccount = user.externalAccounts.find((account) => account.provider === "google");
  const googleSub =
    googleAccount && "providerUserId" in googleAccount
      ? String((googleAccount as { providerUserId: string }).providerUserId)
      : undefined;

  const res = await fetch(`${API_URL}/api/v1/auth/sync`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      "X-Auth-Secret": process.env.AUTH_SECRET || "",
    },
    body: JSON.stringify({
      email,
      name: [user.firstName, user.lastName].filter(Boolean).join(" ") || null,
      image: user.imageUrl,
      google_sub: googleSub,
    }),
  });

  if (!res.ok) {
    const detail = await res.text();
    return NextResponse.json({ error: detail || "Backend auth sync failed" }, { status: 502 });
  }

  return NextResponse.json(await res.json());
}
