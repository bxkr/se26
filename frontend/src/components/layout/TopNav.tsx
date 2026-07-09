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
    "rounded-md px-3 py-1.5 text-sm font-medium transition-colors",
    isActive ? "bg-accent/15 text-accent" : "text-ink-secondary hover:text-ink hover:bg-page",
  );

const mobileNavLinkClass = ({ isActive }: { isActive: boolean }) =>
  clsx(
    "rounded-md px-3 py-2 text-sm font-medium transition-colors",
    isActive ? "bg-accent/15 text-accent" : "text-ink-secondary hover:text-ink hover:bg-page",
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
        <div className="flex items-center gap-6">
          <button
            onClick={() => navigate("/dashboard")}
            className="flex items-center gap-2 font-semibold tracking-tight text-ink"
          >
            <img src="/favicon.svg" alt="" className="h-6 w-6" />
            {strings.app.name}
          </button>
          <nav className="hidden items-center gap-1 md:flex">{navLinks}</nav>
        </div>
        <div className="flex items-center gap-3">
          {isDemo && (
            <span className="hidden rounded-full bg-warning/15 px-2.5 py-0.5 text-xs font-medium text-warning sm:inline-block">
              {strings.nav.demoBadge}
            </span>
          )}
          <button
            onClick={toggleTheme}
            aria-label={strings.nav.theme}
            className="rounded-md border border-border p-1.5 text-ink-secondary hover:text-ink"
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
            className="rounded-md border border-border p-1.5 text-ink-secondary hover:text-ink md:hidden"
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
