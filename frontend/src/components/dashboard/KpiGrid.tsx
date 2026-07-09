import { KpiTile } from "../common/KpiTile";
import { strings } from "../../lib/strings";
import type { ModelMetrics } from "../../types/dashboard";

interface KpiGridProps {
  metrics: ModelMetrics | undefined;
  isLoading: boolean;
}

export function KpiGrid({ metrics, isLoading }: KpiGridProps) {
  const tiles: { label: string; value: number | null | undefined }[] = [
    { label: strings.dashboard.rowsCount, value: metrics?.rows_count },
    { label: strings.dashboard.temperatureMae, value: metrics?.temperature_mae },
    { label: strings.dashboard.temperatureBias, value: metrics?.temperature_bias },
    { label: strings.dashboard.tempMinMae, value: metrics?.temp_min_mae },
    { label: strings.dashboard.tempMinBias, value: metrics?.temp_min_bias },
    { label: strings.dashboard.tempMaxMae, value: metrics?.temp_max_mae },
    { label: strings.dashboard.tempMaxBias, value: metrics?.temp_max_bias },
    { label: strings.dashboard.precipitationMae, value: metrics?.precipitation_mm_mae },
    { label: strings.dashboard.precipitationBias, value: metrics?.precipitation_mm_bias },
  ];

  return (
    <div className="grid grid-cols-2 gap-3 sm:grid-cols-3 lg:grid-cols-4">
      {tiles.map((tile) => (
        <KpiTile key={tile.label} label={tile.label} value={tile.value} isLoading={isLoading} />
      ))}
    </div>
  );
}
