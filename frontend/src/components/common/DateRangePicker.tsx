import { strings } from "../../lib/strings";
import { MAX_REQUEST_RANGE_DAYS, REQUEST_MAX_DATE, REQUEST_MIN_DATE } from "../../lib/constants";
import { Input } from "./Input";

interface DateRangePickerProps {
  from: string;
  to: string;
  onChange: (range: { from: string; to: string }) => void;
  showForecastHint?: boolean;
}

const DAY_MS = 24 * 60 * 60 * 1000;

function clamp(value: string): string {
  if (value < REQUEST_MIN_DATE) return REQUEST_MIN_DATE;
  if (value > REQUEST_MAX_DATE) return REQUEST_MAX_DATE;
  return value;
}

function addDays(value: string, days: number): string {
  return new Date(new Date(value).getTime() + days * DAY_MS).toISOString().slice(0, 10);
}

export function DateRangePicker({ from, to, onChange, showForecastHint }: DateRangePickerProps) {
  return (
    <div className="flex flex-wrap items-end gap-3">
      <Input
        type="date"
        label={strings.filters.dateFrom}
        value={from}
        min={REQUEST_MIN_DATE}
        max={REQUEST_MAX_DATE}
        onChange={(e) => {
          const nextFrom = clamp(e.target.value);
          const cappedTo = clamp(addDays(nextFrom, MAX_REQUEST_RANGE_DAYS - 1));
          onChange({ from: nextFrom, to: nextFrom > to ? nextFrom : to > cappedTo ? cappedTo : to });
        }}
      />
      <Input
        type="date"
        label={strings.filters.dateTo}
        value={to}
        min={from > REQUEST_MIN_DATE ? from : REQUEST_MIN_DATE}
        max={REQUEST_MAX_DATE}
        onChange={(e) => {
          const nextTo = clamp(e.target.value);
          const cappedFrom = clamp(addDays(nextTo, -(MAX_REQUEST_RANGE_DAYS - 1)));
          onChange({ from: from < cappedFrom ? cappedFrom : from, to: nextTo });
        }}
      />
      {showForecastHint && (
        <p className="max-w-xs text-xs text-warning">{strings.filters.forecastMinDateHint}</p>
      )}
      <p className="max-w-xs text-xs text-ink-muted">{strings.filters.rangeTooLarge}</p>
    </div>
  );
}
