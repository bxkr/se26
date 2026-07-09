import { apiGet, BASE_URL } from "../client";
import type { RequestStatus } from "../../types/requests";

export function getRequestStatus(requestId: string): Promise<RequestStatus> {
  return apiGet(`/requests/${requestId}`);
}

export function openRequestStream(requestId: string): EventSource {
  return new EventSource(`${BASE_URL}/requests/${requestId}/stream`, {
    withCredentials: true,
  });
}
