import { SignUp } from "@clerk/nextjs";

export default function SignUpPage() {
  return (
    <div className="min-h-screen flex items-center justify-center bg-margin-bg text-white">
      <SignUp routing="path" path="/sign-up" signInUrl="/sign-in" forceRedirectUrl="/discovery" />
    </div>
  );
}
