import { LineChart, type LineSeries } from "../common/LineChart";
import { strings } from "../../lib/strings";
import type { ModelMetricsDailyRow } from "../../types/dashboard";

interface DashboardTrendChartProps {
  rows: ModelMetricsDailyRow[];
}

type NumericMetricKey = Exclude<keyof ModelMetricsDailyRow, "day" | "rows_count">;

const MAE_FIELDS: { key: NumericMetricKey; label: string; color: string }[] = [
  { key: "temperature_mae", label: "Темп.", color: "rgb(var(--wp-accent))" },
  { key: "temp_min_mae", label: "Мин. темп.", color: "#1baf7a" },
  { key: "temp_max_mae", label: "Макс. темп.", color: "#eda100" },
];

const BIAS_FIELDS: { key: NumericMetricKey; label: string; color: string }[] = [
  { key: "temperature_bias", label: "Темп.", color: "rgb(var(--wp-gauge))" },
  { key: "precipitation_mm_bias", label: "Осадки", color: "#4a3aa7" },
];

function buildSeries(
  rows: ModelMetricsDailyRow[],
  fields: { key: NumericMetricKey; label: string; color: string }[],
): LineSeries[] {
  return fields.map((f) => ({
    key: f.key,
    label: f.label,
    color: f.color,
    points: rows.map((r) => ({ date: new Date(r.day), value: r[f.key] })),
  }));
}

export function DashboardTrendChart({ rows }: DashboardTrendChartProps) {
  if (rows.length === 0) {
    return <p className="py-8 text-center text-sm text-ink-muted">{strings.dashboard.trendEmpty}</p>;
  }

  return (
    <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
      <div className="rounded-md border border-border bg-surface p-4">
        <h3 className="mb-2 text-sm font-medium text-ink-secondary">{strings.dashboard.maeTrend}</h3>
        <LineChart series={buildSeries(rows, MAE_FIELDS)} />
      </div>
      <div className="rounded-md border border-border bg-surface p-4">
        <h3 className="mb-2 text-sm font-medium text-ink-secondary">{strings.dashboard.biasTrend}</h3>
        <LineChart series={buildSeries(rows, BIAS_FIELDS)} />
      </div>
    </div>
  );
}
