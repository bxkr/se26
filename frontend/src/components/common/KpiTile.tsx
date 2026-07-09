import { Sparkline } from "./Sparkline";
import { Skeleton } from "./Skeleton";

interface KpiTileProps {
  label: string;
  value: number | null | undefined;
  unit?: string;
  trend?: number[];
  isLoading?: boolean;
}

function formatValue(value: number | null | undefined, unit?: string): string {
  if (value === null || value === undefined) return "—";
  const formatted = new Intl.NumberFormat("ru-RU", { maximumFractionDigits: 2 }).format(value);
  return unit ? `${formatted} ${unit}` : formatted;
}

export function KpiTile({ label, value, unit, trend, isLoading }: KpiTileProps) {
  return (
    <div className="relative flex flex-col gap-2.5 rounded-md border border-border border-t-2 border-t-gauge/70 bg-surface p-4">
      <span aria-hidden className="absolute right-3 top-3 h-1.5 w-1.5 rounded-full bg-gauge/70" />
      <span className="pr-4 font-mono text-[11px] uppercase tracking-widest text-ink-muted">{label}</span>
      <div className="flex items-end justify-between gap-3">
        {isLoading ? (
          <Skeleton className="h-8 w-20" />
        ) : (
          <span className="font-display text-2xl font-semibold tabular-nums text-ink">
            {formatValue(value, unit)}
          </span>
        )}
        {trend && trend.length > 1 && <Sparkline values={trend} />}
      </div>
    </div>
  );
}
