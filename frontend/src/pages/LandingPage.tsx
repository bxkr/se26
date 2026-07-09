import { useNavigate } from "react-router-dom";
import { useAuth } from "../context/AuthContext";
import { strings } from "../lib/strings";
import { Button } from "../components/common/Button";

export function LandingPage() {
  const navigate = useNavigate();
  const { demoLogin, isLoggingIn } = useAuth();

  async function handleDemo() {
    await demoLogin();
    navigate("/dashboard");
  }

  return (
    <div className="flex min-h-screen flex-col items-center justify-center gap-8 bg-page px-4 text-center">
      <div className="flex flex-col items-center gap-3">
        <span className="font-mono text-sm uppercase tracking-widest text-accent">
          {strings.app.name}
        </span>
        <h1 className="max-w-xl text-3xl font-semibold text-ink sm:text-4xl">
          {strings.landing.pitch}
        </h1>
      </div>
      <div className="flex flex-col items-center gap-3 sm:flex-row">
        <Button variant="primary" onClick={() => navigate("/login")}>
          {strings.landing.signIn}
        </Button>
        <Button variant="secondary" onClick={handleDemo} disabled={isLoggingIn}>
          {strings.landing.demo}
        </Button>
      </div>
    </div>
  );
}
