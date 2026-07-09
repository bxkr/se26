export type RequestStatusValue = "pending" | "ready" | "failed";

export interface RequestStatus {
  request_id: string;
  status: RequestStatusValue;
  created_at: string;
  updated_at: string;
  error_message?: string | null;
}

export type AsyncResult<T> =
  | { status: "ready"; data: T }
  | { status: "pending"; request_id: string };
