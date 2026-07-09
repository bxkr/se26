import { useQuery, type UseQueryResult } from "@tanstack/react-query";
import { apiFetchJson } from "../api/client";
import { openRequestStream } from "../api/endpoints/requests";
import { ApiError } from "../api/errors";
import { strings } from "../lib/strings";
import { POLL_INTERVAL_MS } from "../lib/constants";
import type { AsyncResult, RequestStatus } from "../types/requests";

function sleep(ms: number): Promise<void> {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

async function waitViaPolling(requestId: string, signal: AbortSignal): Promise<RequestStatus> {
  while (true) {
    if (signal.aborted) throw new DOMException("aborted", "AbortError");
    await sleep(POLL_INTERVAL_MS);
    if (signal.aborted) throw new DOMException("aborted", "AbortError");
    const status = await apiFetchJson<RequestStatus>(`/requests/${requestId}`);
    if (status.status !== "pending") return status;
  }
}

function waitViaSSE(requestId: string, signal: AbortSignal): Promise<RequestStatus> {
  return new Promise((resolve, reject) => {
    const es = openRequestStream(requestId);
    const cleanup = () => es.close();

    const onAbort = () => {
      cleanup();
      reject(new DOMException("aborted", "AbortError"));
    };
    signal.addEventListener("abort", onAbort);

    es.addEventListener("ready", (e: MessageEvent) => {
      cleanup();
      resolve(JSON.parse(e.data));
    });
    es.addEventListener("failed", (e: MessageEvent) => {
      cleanup();
      resolve(JSON.parse(e.data));
    });
    es.onerror = () => {
      cleanup();
      reject(new Error("Соединение для отслеживания статуса прервано"));
    };
  });
}

/**
 * Shared implementation of the POST -> 202 pending -> poll/SSE -> re-POST pattern
 * used by all four dashboard endpoints (/regions, /stations, /errors/top, /metrics/model).
 */
export function useAsyncDashboardQuery<TBody, TData>(
  key: readonly unknown[],
  postFn: (body: TBody) => Promise<AsyncResult<TData>>,
  body: TBody | null,
  opts?: { useSSE?: boolean; enabled?: boolean },
): UseQueryResult<TData, Error> {
  return useQuery({
    queryKey: key,
    queryFn: async ({ signal }) => {
      const first = await postFn(body as TBody);
      if (first.status === "ready") return first.data;

      const requestId = first.request_id;
      const finalStatus = opts?.useSSE
        ? await waitViaSSE(requestId, signal)
        : await waitViaPolling(requestId, signal);

      if (finalStatus.status === "failed") {
        throw new ApiError(
          "REQUEST_FAILED",
          finalStatus.error_message ?? strings.async.failed,
          0,
        );
      }

      const second = await postFn(body as TBody);
      if (second.status !== "ready") {
        throw new ApiError("REQUEST_FAILED", strings.async.failed, 0);
      }
      return second.data;
    },
    enabled: (opts?.enabled ?? true) && body !== null,
    retry: false,
    staleTime: 60_000,
  });
}
