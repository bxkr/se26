import { LineChart, type LineSeries } from "../common/LineChart";
import { strings } from "../../lib/strings";
import type { ErrorFieldKey, ForecastErrorRow } from "../../types/dashboard";

interface ExplorerChartsProps {
  rows: ForecastErrorRow[];
}

const SIGNED_FIELDS: { key: ErrorFieldKey; label: string; color: string }[] = [
  { key: "temperature_error", label: "Темп.", color: "rgb(var(--wp-accent))" },
  { key: "temp_min_error", label: "Мин. темп.", color: "#1baf7a" },
  { key: "temp_max_error", label: "Макс. темп.", color: "#eda100" },
];

const ABS_FIELDS: { key: ErrorFieldKey; label: string; color: string }[] = [
  { key: "temperature_abs_error", label: "Темп. (абс.)", color: "rgb(var(--wp-danger))" },
  { key: "precipitation_mm_abs_error", label: "Осадки (абс.)", color: "#4a3aa7" },
];

// A region query returns one row per (station, day) — multiple stations
// share the same day. Charting one point per row put several y-values at
// the same x, which curveMonotoneX then smoothed through as if they were
// sequential, producing loops/spikes instead of a real time series. Average
// across stations per day so each series has exactly one point per x.
function buildSeries(
  rows: ForecastErrorRow[],
  fields: { key: ErrorFieldKey; label: string; color: string }[],
): LineSeries[] {
  const byDay = new Map<string, ForecastErrorRow[]>();
  for (const r of rows) {
    const group = byDay.get(r.day);
    if (group) group.push(r);
    else byDay.set(r.day, [r]);
  }
  const days = [...byDay.keys()].sort((a, b) => a.localeCompare(b));

  return fields.map((f) => ({
    key: f.key,
    label: f.label,
    color: f.color,
    points: days.map((day) => {
      const values = byDay.get(day)!.map((r) => r[f.key]).filter((v): v is number => v !== null);
      const value = values.length > 0 ? values.reduce((a, b) => a + b, 0) / values.length : null;
      return { date: new Date(day), value };
    }),
  }));
}

export function ExplorerCharts({ rows }: ExplorerChartsProps) {
  if (rows.length === 0) {
    return <p className="py-8 text-center text-sm text-ink-muted">{strings.explorer.selectPrompt}</p>;
  }

  return (
    <div className="flex flex-col gap-6">
      <div className="rounded-md border border-border bg-surface p-4">
        <h3 className="mb-2 text-sm font-medium text-ink-secondary">{strings.explorer.actualVsForecast}</h3>
        <LineChart series={buildSeries(rows, SIGNED_FIELDS)} />
      </div>
      <div className="rounded-md border border-border bg-surface p-4">
        <h3 className="mb-2 text-sm font-medium text-ink-secondary">{strings.explorer.errorOverTime}</h3>
        <LineChart series={buildSeries(rows, ABS_FIELDS)} />
      </div>
    </div>
  );
}
