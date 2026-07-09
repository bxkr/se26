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
        viewBox="0 0 1200 360"
        preserveAspectRatio="none"
        className="pointer-events-none absolute inset-x-0 top-1/2 h-[340px] w-full -translate-y-1/2"
      >
        <path
          d="M0,230 L60,220 L120,240 L180,190 L240,200 L300,140 L360,160 L420,110 L480,130 L540,90 L600,120 L660,80 L720,105 L780,70 L840,100 L900,65 L960,95 L1020,75 L1080,105 L1140,85 L1200,110"
          fill="none"
          stroke="rgb(var(--wp-gauge))"
          strokeWidth="2"
          className="hero-contour-1 origin-center opacity-[0.16]"
        />
        <path
          d="M0,160 L60,150 L120,170 L180,120 L240,135 L300,80 L360,100 L420,55 L480,75 L540,35 L600,65 L660,30 L720,50 L780,20 L840,45 L900,15 L960,40 L1020,25 L1080,50 L1140,30 L1200,55"
          fill="none"
          stroke="rgb(var(--wp-accent))"
          strokeWidth="2"
          className="hero-contour-2 origin-center opacity-[0.12]"
        />
        <path
          d="M0,300 L60,290 L120,305 L180,270 L240,280 L300,235 L360,250 L420,210 L480,225 L540,195 L600,220 L660,190 L720,205 L780,175 L840,195 L900,170 L960,190 L1020,178 L1080,198 L1140,182 L1200,200"
          fill="none"
          stroke="rgb(var(--wp-ink-muted))"
          strokeWidth="1.5"
          className="hero-contour-3 origin-center opacity-[0.1]"
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
