import { LoginClient } from "./LoginClient";

type LoginPageProps = {
  searchParams?: { error?: string };
};

export default function LoginPage({ searchParams }: LoginPageProps) {
  const googleEnabled = Boolean(
    process.env.AUTH_GOOGLE_ID && process.env.AUTH_GOOGLE_SECRET,
  );
  const emailEnabled = Boolean(process.env.AUTH_RESEND_KEY);

  return (
    <LoginClient
      error={searchParams?.error}
      googleEnabled={googleEnabled}
      emailEnabled={emailEnabled}
    />
  );
}
