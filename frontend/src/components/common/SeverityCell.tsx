import { severityIntensity } from "../../lib/errorFields";

interface SeverityCellProps {
  value: number | null;
  maxAbs: number;
}

export function SeverityCell({ value, maxAbs }: SeverityCellProps) {
  const intensity = severityIntensity(value, maxAbs);

  return (
    <div className="flex items-center gap-2">
      <span className="w-16 font-mono text-xs tabular-nums text-ink">
        {value === null ? "—" : value.toFixed(2)}
      </span>
      <div className="h-2 flex-1 min-w-10 overflow-hidden rounded-full bg-border/50">
        <div
          className="h-full rounded-full"
          style={{
            width: `${intensity * 100}%`,
            backgroundColor: `color-mix(in oklab, rgb(var(--wp-accent)), rgb(var(--wp-danger)) ${Math.round(intensity * 100)}%)`,
          }}
        />
      </div>
    </div>
  );
}
