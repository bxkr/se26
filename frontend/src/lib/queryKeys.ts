export const queryKeys = {
  authMe: ["auth", "me"] as const,
  adminUsers: ["admin", "users"] as const,
  dashboardMetrics: (params: unknown) => ["dashboard", "metrics", params] as const,
  dashboardMetricsDaily: (params: unknown) => ["dashboard", "metrics-daily", params] as const,
  topErrors: (params: unknown) => ["dashboard", "top-errors", params] as const,
  regionsForecastErrors: (params: unknown) => ["dashboard", "regions", params] as const,
  stationsForecastErrors: (params: unknown) => ["dashboard", "stations", params] as const,
};
