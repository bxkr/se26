import { ERROR_FIELDS } from "../../lib/errorFields";
import { strings } from "../../lib/strings";
import type { ForecastErrorRow } from "../../types/dashboard";
import { CloseIcon } from "../common/Icons";
import { StationTag } from "../common/StationTag";

interface RowDetailDrawerProps {
  row: ForecastErrorRow;
  onClose: () => void;
}

export function RowDetailDrawer({ row, onClose }: RowDetailDrawerProps) {
  return (
    <div className="fixed inset-0 z-50 flex justify-end bg-black/40" onClick={onClose}>
      <div
        className="h-full w-full max-w-sm overflow-y-auto border-l border-border bg-surface p-6"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="mb-4 flex items-center justify-between gap-3">
          <StationTag name={row.station_name} wmoIndex={row.wmo_index} className="text-sm" />
          <button onClick={onClose} aria-label={strings.common.close} className="text-ink-muted hover:text-ink">
            <CloseIcon />
          </button>
        </div>
        <p className="mb-4 font-mono text-sm text-ink-secondary">{row.day}</p>
        <dl className="flex flex-col gap-2">
          {ERROR_FIELDS.map((f) => (
            <div key={f.key} className="flex items-center justify-between border-b border-border py-1.5">
              <dt className="text-sm text-ink-secondary">{f.label}</dt>
              <dd className="font-mono text-sm text-ink">{row[f.key] ?? "—"}</dd>
            </div>
          ))}
          <div className="flex items-center justify-between py-1.5">
            <dt className="text-sm text-ink-secondary">{strings.topErrors.columns.ingestedAt}</dt>
            <dd className="font-mono text-sm text-ink">{row.ingested_at}</dd>
          </div>
        </dl>
      </div>
    </div>
  );
}
