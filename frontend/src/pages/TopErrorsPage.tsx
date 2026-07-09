import { useState } from "react";
import { PageContainer } from "../components/layout/PageContainer";
import { DateRangePicker } from "../components/common/DateRangePicker";
import { AsyncStateBanner } from "../components/common/AsyncStateBanner";
import { Button } from "../components/common/Button";
import { MetricSelect } from "../components/top-errors/MetricSelect";
import { TopErrorsTable } from "../components/top-errors/TopErrorsTable";
import { RowDetailDrawer } from "../components/top-errors/RowDetailDrawer";
import { Select } from "../components/common/Select";
import { useAsyncDashboardQuery } from "../hooks/useAsyncDashboardQuery";
import { errorsTop } from "../api/endpoints/dashboard";
import { queryKeys } from "../lib/queryKeys";
import { strings } from "../lib/strings";
import { DEFAULT_RANGE_FROM, DEFAULT_RANGE_TO } from "../lib/constants";
import type { ErrorFieldKey, ErrorsTopRequest, ForecastErrorRow } from "../types/dashboard";

const LIMIT_OPTIONS = [10, 25, 50, 100];

export function TopErrorsPage() {
  const [draftRange, setDraftRange] = useState({ from: DEFAULT_RANGE_FROM, to: DEFAULT_RANGE_TO });
  const [draftMetric, setDraftMetric] = useState<ErrorFieldKey>("temperature_abs_error");
  const [draftLimit, setDraftLimit] = useState(25);

  const [range, setRange] = useState(draftRange);
  const [metric, setMetric] = useState(draftMetric);
  const [limit, setLimit] = useState(draftLimit);
  const [selectedRow, setSelectedRow] = useState<ForecastErrorRow | null>(null);

  function applyFilters() {
    setRange(draftRange);
    setMetric(draftMetric);
    setLimit(draftLimit);
  }

  const body: ErrorsTopRequest = { from: range.from, to: range.to, metric, limit };
  const { data, isFetching, error, refetch } = useAsyncDashboardQuery(
    queryKeys.topErrors(body),
    errorsTop,
    body,
  );

  return (
    <PageContainer>
      <div className="mb-6 flex flex-col gap-4">
        <h1 className="border-b border-dashed border-border pb-2 font-display text-xl font-semibold text-ink">{strings.topErrors.title}</h1>
        <div className="flex flex-wrap items-end gap-4">
          <DateRangePicker from={draftRange.from} to={draftRange.to} onChange={setDraftRange} showForecastHint />
          <MetricSelect value={draftMetric} onChange={setDraftMetric} />
          <Select
            label={strings.topErrors.limit}
            value={draftLimit}
            onChange={(e) => setDraftLimit(Number(e.target.value))}
          >
            {LIMIT_OPTIONS.map((n) => (
              <option key={n} value={n}>
                {n}
              </option>
            ))}
          </Select>
          <Button onClick={applyFilters}>{strings.filters.apply}</Button>
        </div>
      </div>

      <div className="mb-4">
        <AsyncStateBanner isFetching={isFetching} error={error} onRetry={refetch} />
      </div>

      <TopErrorsTable
        rows={data?.rows ?? []}
        rankedMetric={metric}
        onRowClick={setSelectedRow}
      />

      {selectedRow && <RowDetailDrawer row={selectedRow} onClose={() => setSelectedRow(null)} />}
    </PageContainer>
  );
}
