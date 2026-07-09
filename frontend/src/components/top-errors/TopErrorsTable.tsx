import { DataTable, type DataTableColumn } from "../common/DataTable";
import { SeverityCell } from "../common/SeverityCell";
import { StationTag } from "../common/StationTag";
import { strings } from "../../lib/strings";
import { ERROR_FIELD_LABEL } from "../../lib/errorFields";
import type { ErrorFieldKey, ForecastErrorRow } from "../../types/dashboard";

interface TopErrorsTableProps {
  rows: ForecastErrorRow[];
  rankedMetric: ErrorFieldKey;
  onRowClick: (row: ForecastErrorRow) => void;
}

const DISPLAY_FIELDS: ErrorFieldKey[] = [
  "temperature_error",
  "temp_min_error",
  "temp_max_error",
  "precipitation_mm_error",
];

export function TopErrorsTable({ rows, rankedMetric, onRowClick }: TopErrorsTableProps) {
  const maxAbsByField = Object.fromEntries(
    DISPLAY_FIELDS.map((field) => [
      field,
      Math.max(1e-9, ...rows.map((r) => Math.abs(r[field] ?? 0))),
    ]),
  ) as Record<ErrorFieldKey, number>;

  const columns: DataTableColumn<ForecastErrorRow>[] = [
    {
      key: "wmo_index",
      header: strings.topErrors.columns.wmoIndex,
      render: (r) => <StationTag name={r.station_name} wmoIndex={r.wmo_index} />,
      sortValue: (r) => r.wmo_index,
    },
    {
      key: "day",
      header: strings.topErrors.columns.day,
      render: (r) => <span className="font-mono">{r.day}</span>,
      sortValue: (r) => r.day,
    },
    ...DISPLAY_FIELDS.map((field): DataTableColumn<ForecastErrorRow> => ({
      key: field,
      header: field === rankedMetric ? `${ERROR_FIELD_LABEL[field]} ★` : ERROR_FIELD_LABEL[field],
      align: "right",
      sortValue: (r) => r[field],
      render: (r) => <SeverityCell value={r[field]} maxAbs={maxAbsByField[field]} />,
    })),
  ];

  return (
    <DataTable
      columns={columns}
      rows={rows}
      rowKey={(r) => `${r.wmo_index}-${r.day}`}
      onRowClick={onRowClick}
      emptyMessage={strings.topErrors.empty}
    />
  );
}
