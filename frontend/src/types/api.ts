export type ApiErrorCode =
  | "VALIDATION_ERROR"
  | "UNAUTHORIZED"
  | "FORBIDDEN"
  | "NOT_FOUND"
  | "CONFLICT"
  | "REQUEST_FAILED"
  | "UNKNOWN";

export interface ApiErrorBody {
  error: {
    code: ApiErrorCode;
    message: string;
  };
}
