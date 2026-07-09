import { parseErrorAndThrow } from "./errors";

export const BASE_URL = import.meta.env.VITE_API_BASE_URL as string;

let refreshPromise: Promise<boolean> | null = null;

function refreshOnce(): Promise<boolean> {
  if (!refreshPromise) {
    refreshPromise = fetch(`${BASE_URL}/auth/refresh`, {
      method: "POST",
      credentials: "include",
    })
      .then((r) => r.ok)
      .catch(() => false)
      .finally(() => {
        refreshPromise = null;
      });
  }
  return refreshPromise;
}

const NO_REFRESH_PATHS = ["/auth/refresh", "/auth/login", "/auth/me"];

export async function apiFetch(
  path: string,
  options: RequestInit = {},
  isRetry = false,
): Promise<Response> {
  const hasBody = options.body !== undefined && !(options.headers && "Content-Type" in options.headers);
  const resp = await fetch(`${BASE_URL}${path}`, {
    ...options,
    credentials: "include",
    headers: {
      ...(hasBody ? { "Content-Type": "application/json" } : {}),
      ...options.headers,
    },
  });

  if (resp.status === 401 && !NO_REFRESH_PATHS.includes(path) && !isRetry) {
    const ok = await refreshOnce();
    if (ok) return apiFetch(path, options, true);
  }

  return resp;
}

export async function apiFetchJson<T>(path: string, options?: RequestInit): Promise<T> {
  const resp = await apiFetch(path, options);
  if (!resp.ok) return parseErrorAndThrow(resp);
  if (resp.status === 204) return undefined as T;
  return (await resp.json()) as T;
}

export function apiPost<T>(path: string, body?: unknown): Promise<T> {
  return apiFetchJson<T>(path, {
    method: "POST",
    body: body !== undefined ? JSON.stringify(body) : undefined,
  });
}

export function apiGet<T>(path: string): Promise<T> {
  return apiFetchJson<T>(path, { method: "GET" });
}

export function apiPatch<T>(path: string, body: unknown): Promise<T> {
  return apiFetchJson<T>(path, { method: "PATCH", body: JSON.stringify(body) });
}

export function apiDelete<T>(path: string): Promise<T> {
  return apiFetchJson<T>(path, { method: "DELETE" });
}
