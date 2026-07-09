export type ErrorFieldKey =
  | "temperature_error"
  | "temperature_abs_error"
  | "temp_min_error"
  | "temp_min_abs_error"
  | "temp_max_error"
  | "temp_max_abs_error"
  | "precipitation_mm_error"
  | "precipitation_mm_abs_error";

export interface ForecastErrorRow {
  wmo_index: string;
  station_name?: string | null;
  day: string;
  temperature_error: number | null;
  temperature_abs_error: number | null;
  temp_min_error: number | null;
  temp_min_abs_error: number | null;
  temp_max_error: number | null;
  temp_max_abs_error: number | null;
  precipitation_mm_error: number | null;
  precipitation_mm_abs_error: number | null;
  ingested_at: string;
}

export interface DateRange {
  from: string;
  to: string;
}

export interface RegionsForecastErrorsRequest extends DateRange {
  regions: string[];
}

export interface StationsForecastErrorsRequest extends DateRange {
  stations: string[];
}

export interface ForecastErrorsData {
  rows: ForecastErrorRow[];
}

export interface ErrorsTopRequest extends DateRange {
  metric: ErrorFieldKey;
  limit: number;
}

export interface ErrorsTopData {
  metric: ErrorFieldKey;
  rows: ForecastErrorRow[];
}

export type ModelMetricsRequest = DateRange;

export interface ModelMetrics {
  rows_count: number;
  temperature_mae: number | null;
  temperature_bias: number | null;
  temp_min_mae: number | null;
  temp_min_bias: number | null;
  temp_max_mae: number | null;
  temp_max_bias: number | null;
  precipitation_mm_mae: number | null;
  precipitation_mm_bias: number | null;
}

export interface ModelMetricsDailyRow extends ModelMetrics {
  day: string;
}

export interface ModelMetricsDailyData {
  rows: ModelMetricsDailyRow[];
}
