import { Skeleton } from "../common/Skeleton";

interface BiasScaleProps {
  label: string;
  value: number | null | undefined;
  unit?: string;
  /** Half-range: the track spans [-domain, +domain]. */
  domain: number;
  isLoading?: boolean;
}

function formatValue(value: number | null | undefined, unit?: string): string {
  if (value === null || value === undefined) return "—";
  const formatted = new Intl.NumberFormat("ru-RU", {
    maximumFractionDigits: 2,
    signDisplay: "exceptZero",
  }).format(value);
  return unit ? `${formatted} ${unit}` : formatted;
}

export function BiasScale({ label, value, unit, domain, isLoading }: BiasScaleProps) {
  const clamped = value === null || value === undefined ? 0 : Math.max(-domain, Math.min(domain, value));
  const pct = (clamped / domain) * 50;
  const intensity = value === null || value === undefined ? 0 : Math.min(Math.abs(value) / domain, 1);
  const fillColor = `color-mix(in oklab, rgb(var(--wp-gauge)), rgb(var(--wp-danger)) ${Math.round(intensity * 100)}%)`;

  return (
    <div className="relative flex flex-col gap-2.5 rounded-md border border-border border-t-2 border-t-gauge/70 bg-surface p-4">
      <span aria-hidden className="absolute right-3 top-3 h-1.5 w-1.5 rounded-full bg-gauge/70" />
      <span className="pr-4 font-mono text-[11px] uppercase tracking-widest text-ink-muted">{label}</span>
      {isLoading ? (
        <Skeleton className="h-10 w-full" />
      ) : (
        <>
          <span className="font-display text-xl font-semibold tabular-nums text-ink">
            {formatValue(value, unit)}
          </span>
          <div className="relative h-1.5 w-full rounded-[1px] bg-border/50">
            <span aria-hidden className="absolute inset-y-[-2px] left-1/2 w-px bg-ink-muted/70" />
            <div
              className="absolute inset-y-0"
              style={{
                left: pct >= 0 ? "50%" : `${50 + pct}%`,
                width: `${Math.abs(pct)}%`,
                backgroundColor: fillColor,
              }}
            />
          </div>
          <div className="flex justify-between font-mono text-[10px] text-ink-muted">
            <span>
              −{domain} {unit}
            </span>
            <span>0</span>
            <span>
              +{domain} {unit}
            </span>
          </div>
        </>
      )}
    </div>
  );
}
