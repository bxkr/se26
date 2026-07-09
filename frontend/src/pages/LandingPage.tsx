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
    <div className="chart-grid-paper relative flex min-h-screen flex-col items-center justify-center gap-10 overflow-hidden bg-page px-4 text-center">
      <svg
        aria-hidden
        viewBox="0 0 1200 300"
        preserveAspectRatio="none"
        className="pointer-events-none absolute inset-x-0 top-1/2 h-[280px] w-full -translate-y-1/2 opacity-[0.14]"
      >
        <path
          d="M0,180 L60,170 L120,190 L180,140 L240,150 L300,90 L360,110 L420,60 L480,80 L540,40 L600,70 L660,30 L720,55 L780,20 L840,50 L900,15 L960,45 L1020,25 L1080,55 L1140,35 L1200,60"
          fill="none"
          stroke="rgb(var(--wp-gauge))"
          strokeWidth="2"
        />
      </svg>

      <div className="relative flex flex-col items-center gap-4">
        <span className="flex items-center gap-2 rounded-sm border border-border px-2.5 py-1 font-mono text-xs uppercase tracking-widest text-ink-muted">
          <img src="/favicon.svg" alt="" className="h-4 w-4" />
          {strings.app.name} · {strings.nav.stationLogTag}
        </span>
        <h1 className="max-w-xl font-display text-4xl font-semibold leading-tight text-ink sm:text-5xl">
          {strings.landing.headline}
        </h1>
        <p className="max-w-md text-ink-secondary">{strings.landing.pitch}</p>
      </div>
      <div className="relative flex flex-col items-center gap-3 sm:flex-row">
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
