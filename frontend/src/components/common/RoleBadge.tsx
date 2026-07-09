import clsx from "clsx";
import type { Role } from "../../types/auth";
import { strings } from "../../lib/strings";

export function RoleBadge({ role }: { role: Role }) {
  const isAdmin = role === "admin";
  return (
    <span
      className={clsx(
        "inline-flex items-center rounded-sm border px-2 py-0.5 font-mono text-[11px] uppercase tracking-wide",
        isAdmin ? "border-gauge/50 bg-gauge/10 text-gauge" : "border-border text-ink-secondary",
      )}
    >
      {isAdmin ? strings.roles.admin : strings.roles.user}
    </span>
  );
}
