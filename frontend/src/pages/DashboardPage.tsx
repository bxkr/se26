import { useState } from "react";
import { PageContainer } from "../components/layout/PageContainer";
import { DateRangePicker } from "../components/common/DateRangePicker";
import { AsyncStateBanner } from "../components/common/AsyncStateBanner";
import { Button } from "../components/common/Button";
import { KpiGrid } from "../components/dashboard/KpiGrid";
import { useAsyncDashboardQuery } from "../hooks/useAsyncDashboardQuery";
import { metricsModel } from "../api/endpoints/dashboard";
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

  return (
    <PageContainer>
      <div className="mb-6 flex flex-col gap-4">
        <h1 className="text-xl font-semibold text-ink">{strings.dashboard.title}</h1>
        <div className="flex flex-wrap items-end gap-3">
          <DateRangePicker from={draftRange.from} to={draftRange.to} onChange={setDraftRange} showForecastHint />
          <Button onClick={() => setRange(draftRange)}>{strings.filters.apply}</Button>
        </div>
      </div>

      <div className="mb-4">
        <AsyncStateBanner isFetching={isFetching} error={error} onRetry={refetch} />
      </div>

      <KpiGrid metrics={data} isLoading={isFetching && !data} />
    </PageContainer>
  );
}
