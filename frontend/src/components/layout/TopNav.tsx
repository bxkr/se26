import { useState } from "react";
import { NavLink, useNavigate } from "react-router-dom";
import clsx from "clsx";
import { useAuth } from "../../context/AuthContext";
import { useTheme } from "../../context/ThemeContext";
import { strings } from "../../lib/strings";
import { DEMO_CREDENTIALS } from "../../lib/constants";
import { Button } from "../common/Button";
import { SunIcon, MoonIcon, MenuIcon, CloseIcon } from "../common/Icons";

const navLinkClass = ({ isActive }: { isActive: boolean }) =>
  clsx(
    "relative py-1.5 font-mono text-xs uppercase tracking-wider transition-colors",
    isActive
      ? "text-accent after:absolute after:inset-x-0 after:-bottom-[13px] after:h-0.5 after:bg-accent"
      : "text-ink-secondary hover:text-ink",
  );

const mobileNavLinkClass = ({ isActive }: { isActive: boolean }) =>
  clsx(
    "border-l-2 px-3 py-2 font-mono text-xs uppercase tracking-wider transition-colors",
    isActive ? "border-accent text-accent" : "border-transparent text-ink-secondary hover:text-ink",
  );

export function TopNav() {
  const { user, logout } = useAuth();
  const { theme, toggleTheme } = useTheme();
  const navigate = useNavigate();
  const [menuOpen, setMenuOpen] = useState(false);
  const isDemo = user?.username === DEMO_CREDENTIALS.username;

  const navLinks = (
    <>
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
    </>
  );

  const mobileNavLinks = (
    <>
      <NavLink to="/dashboard" className={mobileNavLinkClass} onClick={() => setMenuOpen(false)}>
        {strings.nav.dashboard}
      </NavLink>
      <NavLink to="/top-errors" className={mobileNavLinkClass} onClick={() => setMenuOpen(false)}>
        {strings.nav.topErrors}
      </NavLink>
      <NavLink to="/explorer" className={mobileNavLinkClass} onClick={() => setMenuOpen(false)}>
        {strings.nav.explorer}
      </NavLink>
      {user?.role === "admin" && (
        <NavLink to="/admin" className={mobileNavLinkClass} onClick={() => setMenuOpen(false)}>
          {strings.nav.admin}
        </NavLink>
      )}
    </>
  );

  return (
    <header className="sticky top-0 z-40 border-b border-border bg-surface/95 backdrop-blur">
      <div className="mx-auto flex max-w-7xl items-center justify-between gap-4 px-4 py-3">
        <div className="flex items-center gap-7">
          <button
            onClick={() => navigate("/dashboard")}
            className="flex items-center gap-2.5 font-display text-lg font-semibold tracking-tight text-ink"
          >
            <img src="/favicon.svg" alt="" className="h-6 w-6" />
            {strings.app.name}
            <span className="hidden rounded-sm border border-border px-1.5 py-0.5 font-mono text-[10px] font-normal tracking-widest text-ink-muted sm:inline">
              {strings.nav.stationLogTag}
            </span>
          </button>
          <nav className="hidden items-center gap-6 md:flex">{navLinks}</nav>
        </div>
        <div className="flex items-center gap-3">
          {isDemo && (
            <span className="hidden rounded-sm border border-warning/40 px-2 py-0.5 font-mono text-[10px] uppercase tracking-widest text-warning sm:inline-block">
              {strings.nav.demoBadge}
            </span>
          )}
          <button
            onClick={toggleTheme}
            aria-label={strings.nav.theme}
            className="rounded-sm border border-border p-1.5 text-ink-secondary hover:text-ink"
          >
            {theme === "dark" ? <SunIcon /> : <MoonIcon />}
          </button>
          <span className="hidden font-mono text-sm text-ink-secondary sm:inline">{user?.username}</span>
          <Button variant="secondary" onClick={() => logout()} className="hidden md:inline-flex">
            {strings.nav.logout}
          </Button>
          <button
            onClick={() => setMenuOpen((v) => !v)}
            aria-label={strings.nav.menu}
            aria-expanded={menuOpen}
            className="rounded-sm border border-border p-1.5 text-ink-secondary hover:text-ink md:hidden"
          >
            {menuOpen ? <CloseIcon /> : <MenuIcon />}
          </button>
        </div>
      </div>
      {menuOpen && (
        <nav className="flex flex-col gap-1 border-t border-border bg-surface px-4 py-3 md:hidden">
          {mobileNavLinks}
          <div className="mt-2 border-t border-border pt-3">
            <span className="font-mono text-sm text-ink-secondary">{user?.username}</span>
          </div>
        </nav>
      )}
    </header>
  );
}
