import { Select } from "../common/Select";
import { ERROR_FIELDS } from "../../lib/errorFields";
import { strings } from "../../lib/strings";
import type { ErrorFieldKey } from "../../types/dashboard";

interface MetricSelectProps {
  value: ErrorFieldKey;
  onChange: (value: ErrorFieldKey) => void;
}

export function MetricSelect({ value, onChange }: MetricSelectProps) {
  return (
    <Select
      label={strings.topErrors.metric}
      value={value}
      onChange={(e) => onChange(e.target.value as ErrorFieldKey)}
    >
      {ERROR_FIELDS.map((f) => (
        <option key={f.key} value={f.key}>
          {f.label}
        </option>
      ))}
    </Select>
  );
}
