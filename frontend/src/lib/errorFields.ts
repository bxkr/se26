import type { ErrorFieldKey } from "../types/dashboard";

export interface ErrorFieldDef {
  key: ErrorFieldKey;
  label: string;
  abs: boolean;
}

export const ERROR_FIELDS: ErrorFieldDef[] = [
  { key: "temperature_error", label: "Ошибка темп.", abs: false },
  { key: "temperature_abs_error", label: "Ошибка темп. (абс.)", abs: true },
  { key: "temp_min_error", label: "Ошибка мин. темп.", abs: false },
  { key: "temp_min_abs_error", label: "Ошибка мин. темп. (абс.)", abs: true },
  { key: "temp_max_error", label: "Ошибка макс. темп.", abs: false },
  { key: "temp_max_abs_error", label: "Ошибка макс. темп. (абс.)", abs: true },
  { key: "precipitation_mm_error", label: "Ошибка осадков", abs: false },
  { key: "precipitation_mm_abs_error", label: "Ошибка осадков (абс.)", abs: true },
];

export const ERROR_FIELD_LABEL: Record<ErrorFieldKey, string> = Object.fromEntries(
  ERROR_FIELDS.map((f) => [f.key, f.label]),
) as Record<ErrorFieldKey, string>;

/**
 * Severity intensity 0..1 for a value relative to the max magnitude in its column —
 * drives the accent -> danger interpolation used by SeverityCell.
 */
export function severityIntensity(value: number | null, maxAbs: number): number {
  if (value === null || maxAbs === 0) return 0;
  return Math.min(Math.abs(value) / maxAbs, 1);
}
