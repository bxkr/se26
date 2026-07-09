import { apiPost } from "../client";
import type { AsyncResult } from "../../types/requests";
import type {
  ErrorsTopData,
  ErrorsTopRequest,
  ForecastErrorsData,
  ModelMetrics,
  ModelMetricsDailyData,
  ModelMetricsRequest,
  RegionsForecastErrorsRequest,
  StationsForecastErrorsRequest,
} from "../../types/dashboard";

export function regionsForecastErrors(
  body: RegionsForecastErrorsRequest,
): Promise<AsyncResult<ForecastErrorsData>> {
  return apiPost("/regions/forecast-errors", body);
}

export function stationsForecastErrors(
  body: StationsForecastErrorsRequest,
): Promise<AsyncResult<ForecastErrorsData>> {
  return apiPost("/stations/forecast-errors", body);
}

export function errorsTop(body: ErrorsTopRequest): Promise<AsyncResult<ErrorsTopData>> {
  return apiPost("/errors/top", body);
}

export function metricsModel(body: ModelMetricsRequest): Promise<AsyncResult<ModelMetrics>> {
  return apiPost("/metrics/model", body);
}

export function metricsModelDaily(body: ModelMetricsRequest): Promise<AsyncResult<ModelMetricsDailyData>> {
  return apiPost("/metrics/model/daily", body);
}
