import { strings } from "../../lib/strings";
import { REQUEST_MAX_DATE, REQUEST_MIN_DATE } from "../../lib/constants";
import { Input } from "./Input";

interface DateRangePickerProps {
  from: string;
  to: string;
  onChange: (range: { from: string; to: string }) => void;
  showForecastHint?: boolean;
}

function clamp(value: string): string {
  if (value < REQUEST_MIN_DATE) return REQUEST_MIN_DATE;
  if (value > REQUEST_MAX_DATE) return REQUEST_MAX_DATE;
  return value;
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
          onChange({ from: nextFrom, to: nextFrom > to ? nextFrom : to });
        }}
      />
      <Input
        type="date"
        label={strings.filters.dateTo}
        value={to}
        min={from > REQUEST_MIN_DATE ? from : REQUEST_MIN_DATE}
        max={REQUEST_MAX_DATE}
        onChange={(e) => onChange({ from, to: clamp(e.target.value) })}
      />
      {showForecastHint && (
        <p className="max-w-xs text-xs text-warning">{strings.filters.forecastMinDateHint}</p>
      )}
    </div>
  );
}
