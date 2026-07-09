import { NavLink } from "react-router-dom";
import clsx from "clsx";
import { useAuth } from "../../context/AuthContext";
import { useTheme } from "../../context/ThemeContext";
import { strings } from "../../lib/strings";
import { DEMO_CREDENTIALS } from "../../lib/constants";
import { Button } from "../common/Button";

const navLinkClass = ({ isActive }: { isActive: boolean }) =>
  clsx(
    "rounded-md px-3 py-1.5 text-sm font-medium transition-colors",
    isActive ? "bg-accent/15 text-accent" : "text-ink-secondary hover:text-ink hover:bg-page",
  );

export function TopNav() {
  const { user, logout } = useAuth();
  const { theme, toggleTheme } = useTheme();
  const isDemo = user?.username === DEMO_CREDENTIALS.username;

  return (
    <header className="sticky top-0 z-40 border-b border-border bg-surface/95 backdrop-blur">
      <div className="mx-auto flex max-w-7xl items-center justify-between gap-4 px-4 py-3">
        <div className="flex items-center gap-6">
          <span className="font-semibold tracking-tight text-ink">{strings.app.name}</span>
          <nav className="flex items-center gap-1">
            <NavLink to="/dashboard" className={navLinkClass}>
              {strings.nav.dashboard}
            </NavLink>
            <NavLink to="/top-errors" className={navLinkClass}>
              {strings.nav.topErrors}
            </NavLink>
            <NavLink to="/explorer" className={navLinkClass}>
              {strings.nav.explorer}
            </NavLink>
            {user?.role === "admin" && (
              <NavLink to="/admin" className={navLinkClass}>
                {strings.nav.admin}
              </NavLink>
            )}
          </nav>
        </div>
        <div className="flex items-center gap-3">
          {isDemo && (
            <span className="rounded-full bg-warning/15 px-2.5 py-0.5 text-xs font-medium text-warning">
              {strings.nav.demoBadge}
            </span>
          )}
          <button
            onClick={toggleTheme}
            aria-label={strings.nav.theme}
            className="rounded-md border border-border p-1.5 text-ink-secondary hover:text-ink"
          >
            {theme === "dark" ? "☀️" : "🌙"}
          </button>
          <span className="font-mono text-sm text-ink-secondary">{user?.username}</span>
          <Button variant="secondary" onClick={() => logout()}>
            {strings.nav.logout}
          </Button>
        </div>
      </div>
    </header>
  );
}
