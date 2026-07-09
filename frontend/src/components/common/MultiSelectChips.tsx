import clsx from "clsx";

interface MultiSelectChipsProps {
  options: string[];
  selected: string[];
  onChange: (selected: string[]) => void;
  label?: string;
}

export function MultiSelectChips({ options, selected, onChange, label }: MultiSelectChipsProps) {
  function toggle(option: string) {
    if (selected.includes(option)) {
      onChange(selected.filter((o) => o !== option));
    } else {
      onChange([...selected, option]);
    }
  }

  return (
    <div className="flex flex-col gap-1.5">
      {label && <span className="text-sm text-ink-secondary">{label}</span>}
      <div className="flex flex-wrap gap-2">
        {options.map((option) => {
          const active = selected.includes(option);
          return (
            <button
              key={option}
              type="button"
              onClick={() => toggle(option)}
              className={clsx(
                "rounded-sm border px-3 py-1 font-mono text-xs uppercase tracking-wide transition-colors",
                active
                  ? "border-accent bg-accent/15 text-accent"
                  : "border-border bg-surface text-ink-secondary hover:border-ink-muted",
              )}
            >
              {option}
            </button>
          );
        })}
      </div>
    </div>
  );
}
