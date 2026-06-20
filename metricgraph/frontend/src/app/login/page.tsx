"use client";

import { signIn } from "next-auth/react";

export default function LoginPage() {
  return (
    <div className="min-h-screen flex bg-margin-bg text-white login-root">
      <div className="hidden lg:flex lg:w-1/2 flex-col justify-center px-16 bg-gradient-to-br from-indigo-950 via-margin-bg to-margin-bg border-r border-margin-border">
        <p className="text-sm uppercase tracking-widest text-margin-muted mb-4">Margin Registry</p>
        <h1 className="text-4xl font-semibold leading-tight mb-4">
          Investment metrics with context
        </h1>
        <p className="text-margin-muted max-w-md">
          Explore your knowledge graph, review Linear queries, and govern metrics in one workspace.
        </p>
      </div>
      <div className="flex flex-1 flex-col justify-center px-8 lg:px-16">
        <div className="max-w-sm w-full mx-auto">
          <h2 className="text-2xl font-semibold mb-2">Sign in</h2>
          <p className="text-margin-muted text-sm mb-8">Use Google or your work email</p>
          <button
            type="button"
            onClick={() => signIn("google", { callbackUrl: "/discovery" })}
            className="w-full mb-3 rounded-lg bg-white text-gray-900 py-3 px-4 font-medium hover:bg-gray-100 transition"
          >
            Continue with Google
          </button>
          <button
            type="button"
            onClick={() => signIn("email", { callbackUrl: "/discovery" })}
            className="w-full rounded-lg border border-margin-border py-3 px-4 font-medium hover:bg-margin-surface transition"
          >
            Continue with Email
          </button>
        </div>
      </div>
    </div>
  );
}
