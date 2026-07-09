import type { InputHTMLAttributes } from "react";
import clsx from "clsx";

interface InputProps extends InputHTMLAttributes<HTMLInputElement> {
  label?: string;
}

export function Input({ label, className, id, ...props }: InputProps) {
  return (
    <label className="flex flex-col gap-1 text-sm">
      {label && <span className="text-ink-secondary">{label}</span>}
      <input
        id={id}
        className={clsx(
          "rounded-md border border-border bg-surface px-3 py-2 text-ink outline-none focus:border-accent",
          className,
        )}
        {...props}
      />
    </label>
  );
}
