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
    <div className="flex flex-col gap-2 rounded-lg border border-border bg-surface p-4">
      <span className="text-xs font-medium uppercase tracking-wide text-ink-muted">{label}</span>
      <div className="flex items-end justify-between gap-2">
        {isLoading ? (
          <Skeleton className="h-7 w-16" />
        ) : (
          <span className="font-mono text-2xl font-semibold text-ink">
            {formatValue(value, unit)}
          </span>
        )}
        {trend && trend.length > 1 && <Sparkline values={trend} />}
      </div>
    </div>
  );
}
