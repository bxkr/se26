import { useState } from "react";
import { useParams } from "react-router-dom";
import { PageContainer } from "../components/layout/PageContainer";
import { DateRangePicker } from "../components/common/DateRangePicker";
import { AsyncStateBanner } from "../components/common/AsyncStateBanner";
import { Button } from "../components/common/Button";
import { RegionStationPicker, type ExplorerMode } from "../components/explorer/RegionStationPicker";
import { ExplorerCharts } from "../components/explorer/ExplorerCharts";
import { useAsyncDashboardQuery } from "../hooks/useAsyncDashboardQuery";
import { regionsForecastErrors, stationsForecastErrors } from "../api/endpoints/dashboard";
import { queryKeys } from "../lib/queryKeys";
import { strings } from "../lib/strings";
import { EXPLORER_DEFAULT_RANGE_FROM, EXPLORER_DEFAULT_RANGE_TO } from "../lib/constants";

export function ExplorerPage() {
  const { wmoIndex } = useParams();
  const [draftMode, setDraftMode] = useState<ExplorerMode>(wmoIndex ? "station" : "region");
  const [draftSelected, setDraftSelected] = useState<string[]>(wmoIndex ? [wmoIndex] : []);
  const [draftRange, setDraftRange] = useState({ from: EXPLORER_DEFAULT_RANGE_FROM, to: EXPLORER_DEFAULT_RANGE_TO });

  const [mode, setMode] = useState(draftMode);
  const [selected, setSelected] = useState(draftSelected);
  const [range, setRange] = useState(draftRange);

  function applyFilters() {
    setMode(draftMode);
    setSelected(draftSelected);
    setRange(draftRange);
  }

  const regionBody = mode === "region" && selected.length > 0 ? { from: range.from, to: range.to, regions: selected } : null;
  const stationBody = mode === "station" && selected.length > 0 ? { from: range.from, to: range.to, stations: selected } : null;

  const regionsQuery = useAsyncDashboardQuery(
    queryKeys.regionsForecastErrors(regionBody),
    regionsForecastErrors,
    regionBody,
  );
  const stationsQuery = useAsyncDashboardQuery(
    queryKeys.stationsForecastErrors(stationBody),
    stationsForecastErrors,
    stationBody,
  );

  const active = mode === "region" ? regionsQuery : stationsQuery;

  return (
    <PageContainer>
      <div className="mb-6 flex flex-col gap-4">
        <h1 className="border-b border-dashed border-border pb-2 font-display text-xl font-semibold text-ink">{strings.explorer.title}</h1>
        <div className="flex flex-wrap items-end gap-6">
          <div className="w-72">
            <RegionStationPicker
              mode={draftMode}
              onModeChange={setDraftMode}
              selected={draftSelected}
              onChange={setDraftSelected}
            />
          </div>
          <DateRangePicker from={draftRange.from} to={draftRange.to} onChange={setDraftRange} showForecastHint />
          <Button onClick={applyFilters}>{strings.filters.apply}</Button>
        </div>
      </div>

      <div className="mb-4">
        <AsyncStateBanner isFetching={active.isFetching} error={active.error} onRetry={active.refetch} />
      </div>

      <ExplorerCharts rows={active.data?.rows ?? []} />
    </PageContainer>
  );
}
