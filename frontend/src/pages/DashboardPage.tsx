import { useState } from "react";
import { PageContainer } from "../components/layout/PageContainer";
import { DateRangePicker } from "../components/common/DateRangePicker";
import { AsyncStateBanner } from "../components/common/AsyncStateBanner";
import { Button } from "../components/common/Button";
import { GaugeDial } from "../components/dashboard/GaugeDial";
import { BiasScale } from "../components/dashboard/BiasScale";
import { DashboardTrendChart } from "../components/dashboard/DashboardTrendChart";
import { useAsyncDashboardQuery } from "../hooks/useAsyncDashboardQuery";
import { metricsModel, metricsModelDaily } from "../api/endpoints/dashboard";
import { queryKeys } from "../lib/queryKeys";
import { strings } from "../lib/strings";
import { DEFAULT_RANGE_FROM, DEFAULT_RANGE_TO } from "../lib/constants";
import type { ModelMetricsRequest } from "../types/dashboard";

export function DashboardPage() {
  const [draftRange, setDraftRange] = useState({ from: DEFAULT_RANGE_FROM, to: DEFAULT_RANGE_TO });
  const [range, setRange] = useState(draftRange);

  const body: ModelMetricsRequest = { from: range.from, to: range.to };
  const { data, isFetching, error, refetch } = useAsyncDashboardQuery(
    queryKeys.dashboardMetrics(body),
    metricsModel,
    body,
  );
  const daily = useAsyncDashboardQuery(queryKeys.dashboardMetricsDaily(body), metricsModelDaily, body);

  const isLoading = isFetching && !data;

  return (
    <PageContainer>
      <div className="mb-6 flex flex-col gap-4">
        <div className="flex flex-wrap items-baseline justify-between gap-2 border-b border-dashed border-border pb-2">
          <h1 className="font-display text-xl font-semibold text-ink">{strings.dashboard.title}</h1>
          {data && (
            <span className="font-mono text-xs text-ink-muted">
              {strings.dashboard.rowsCount}: {new Intl.NumberFormat("ru-RU").format(data.rows_count)}
            </span>
          )}
        </div>
        <div className="flex flex-wrap items-end gap-3">
          <DateRangePicker from={draftRange.from} to={draftRange.to} onChange={setDraftRange} showForecastHint />
          <Button onClick={() => setRange(draftRange)}>{strings.filters.apply}</Button>
        </div>
      </div>

      <div className="mb-4">
        <AsyncStateBanner isFetching={isFetching} error={error} onRetry={refetch} />
      </div>

      <div className="mb-3 grid grid-cols-2 gap-3 lg:grid-cols-4">
        <GaugeDial
          label={strings.dashboard.temperatureMae}
          value={data?.temperature_mae}
          unit="°C"
          good={1}
          warning={2.5}
          max={4}
          isLoading={isLoading}
        />
        <GaugeDial
          label={strings.dashboard.tempMinMae}
          value={data?.temp_min_mae}
          unit="°C"
          good={1}
          warning={2.5}
          max={4}
          isLoading={isLoading}
        />
        <GaugeDial
          label={strings.dashboard.tempMaxMae}
          value={data?.temp_max_mae}
          unit="°C"
          good={1}
          warning={2.5}
          max={4}
          isLoading={isLoading}
        />
        <GaugeDial
          label={strings.dashboard.precipitationMae}
          value={data?.precipitation_mm_mae}
          unit="mm"
          good={1}
          warning={3}
          max={6}
          isLoading={isLoading}
        />
      </div>

      <div className="mb-6 grid grid-cols-2 gap-3 lg:grid-cols-4">
        <BiasScale
          label={strings.dashboard.temperatureBias}
          value={data?.temperature_bias}
          unit="°C"
          domain={3}
          isLoading={isLoading}
        />
        <BiasScale
          label={strings.dashboard.tempMinBias}
          value={data?.temp_min_bias}
          unit="°C"
          domain={3}
          isLoading={isLoading}
        />
        <BiasScale
          label={strings.dashboard.tempMaxBias}
          value={data?.temp_max_bias}
          unit="°C"
          domain={3}
          isLoading={isLoading}
        />
        <BiasScale
          label={strings.dashboard.precipitationBias}
          value={data?.precipitation_mm_bias}
          unit="mm"
          domain={3}
          isLoading={isLoading}
        />
      </div>

      <div className="mb-3">
        <AsyncStateBanner isFetching={daily.isFetching} error={daily.error} onRetry={daily.refetch} />
      </div>
      <DashboardTrendChart rows={daily.data?.rows ?? []} />
    </PageContainer>
  );
}
