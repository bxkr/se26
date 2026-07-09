import type { SelectHTMLAttributes } from "react";
import clsx from "clsx";

interface SelectProps extends SelectHTMLAttributes<HTMLSelectElement> {
  label?: string;
}

export function Select({ label, className, children, id, ...props }: SelectProps) {
  return (
    <label className="flex flex-col gap-1 text-sm">
      {label && <span className="text-ink-secondary">{label}</span>}
      <select
        id={id}
        className={clsx(
          "rounded-md border border-border bg-surface px-3 py-2 text-ink outline-none focus:border-accent",
          className,
        )}
        {...props}
      >
        {children}
      </select>
    </label>
  );
}
