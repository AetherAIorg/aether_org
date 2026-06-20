import { withAuth } from "next-auth/middleware";
import { NextResponse } from "next/server";

export default process.env.AUTH_SECRET
  ? withAuth({
      pages: { signIn: "/login" },
    })
  : () => NextResponse.next();

export const config = {
  matcher: [
    "/((?!login|api/auth|_next/static|_next/image|favicon.ico).*)",
  ],
};
