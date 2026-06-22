import { SignIn } from "@clerk/nextjs";

export default function SignInPage() {
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
        <div className="max-w-sm w-full mx-auto flex justify-center">
          <SignIn
            routing="path"
            path="/sign-in"
            signUpUrl="/sign-up"
            forceRedirectUrl="/discovery"
          />
        </div>
      </div>
    </div>
  );
}
