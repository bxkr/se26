import clsx from "clsx";
import type { Role } from "../../types/auth";
import { strings } from "../../lib/strings";

export function RoleBadge({ role }: { role: Role }) {
  const isAdmin = role === "admin";
  return (
    <span
      className={clsx(
        "inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-medium",
        isAdmin
          ? "bg-accent/15 text-accent"
          : "bg-ink-muted/15 text-ink-secondary",
      )}
    >
      {isAdmin ? strings.roles.admin : strings.roles.user}
    </span>
  );
}
