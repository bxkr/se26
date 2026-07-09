import { Skeleton } from "../common/Skeleton";

interface GaugeDialProps {
  label: string;
  value: number | null | undefined;
  unit?: string;
  /** Upper bound of the "good" (green) band. */
  good: number;
  /** Upper bound of the "caution" (brass) band — beyond it is the "poor" (red) band. */
  warning: number;
  /** Needle pins at this value even if the real value is higher. */
  max: number;
  isLoading?: boolean;
}

const CX = 100;
const CY = 96;
const R = 78;
const TICKS = 5;

function point(t: number, r: number): { x: number; y: number } {
  const theta = Math.PI - t * Math.PI;
  return { x: CX + r * Math.cos(theta), y: CY - r * Math.sin(theta) };
}

function arcPath(t0: number, t1: number, r: number): string {
  const p0 = point(t0, r);
  const p1 = point(t1, r);
  const largeArc = t1 - t0 > 0.5 ? 1 : 0;
  return `M ${p0.x} ${p0.y} A ${r} ${r} 0 ${largeArc} 1 ${p1.x} ${p1.y}`;
}

function formatValue(value: number | null | undefined, unit?: string): string {
  if (value === null || value === undefined) return "—";
  const formatted = new Intl.NumberFormat("ru-RU", { maximumFractionDigits: 2 }).format(value);
  return unit ? `${formatted} ${unit}` : formatted;
}

export function GaugeDial({ label, value, unit, good, warning, max, isLoading }: GaugeDialProps) {
  const tGood = good / max;
  const tWarning = warning / max;
  const t = value === null || value === undefined ? 0 : Math.min(Math.abs(value), max) / max;
  const needle = point(t, R - 6);

  return (
    <div className="relative flex flex-col items-center gap-1 rounded-md border border-border border-t-2 border-t-gauge/70 bg-surface p-4">
      <span aria-hidden className="absolute right-3 top-3 h-1.5 w-1.5 rounded-full bg-gauge/70" />
      <span className="self-start pr-4 font-mono text-[11px] uppercase tracking-widest text-ink-muted">
        {label}
      </span>
      {isLoading ? (
        <Skeleton className="h-[104px] w-[200px]" />
      ) : (
        <svg viewBox="0 0 200 108" className="w-full max-w-[220px]">
          <path
            d={arcPath(0, tGood, R)}
            fill="none"
            stroke="rgb(var(--wp-good))"
            strokeWidth={10}
            strokeLinecap="round"
          />
          <path
            d={arcPath(tGood, tWarning, R)}
            fill="none"
            stroke="rgb(var(--wp-gauge))"
            strokeWidth={10}
          />
          <path
            d={arcPath(tWarning, 1, R)}
            fill="none"
            stroke="rgb(var(--wp-danger))"
            strokeWidth={10}
            strokeLinecap="round"
          />
          {Array.from({ length: TICKS }, (_, i) => {
            const ti = i / (TICKS - 1);
            const inner = point(ti, R - 12);
            const outer = point(ti, R + 2);
            return (
              <line
                key={ti}
                x1={inner.x}
                y1={inner.y}
                x2={outer.x}
                y2={outer.y}
                stroke="rgb(var(--wp-surface))"
                strokeWidth={2}
              />
            );
          })}
          <line
            x1={CX}
            y1={CY}
            x2={needle.x}
            y2={needle.y}
            stroke="rgb(var(--wp-ink))"
            strokeWidth={2}
            strokeLinecap="round"
          />
          <circle cx={CX} cy={CY} r={5} fill="rgb(var(--wp-gauge))" />
          <text
            x={CX}
            y={CY - 20}
            textAnchor="middle"
            className="font-display"
            fontSize={22}
            fontWeight={600}
            fill="rgb(var(--wp-ink))"
          >
            {formatValue(value, unit)}
          </text>
        </svg>
      )}
    </div>
  );
}
