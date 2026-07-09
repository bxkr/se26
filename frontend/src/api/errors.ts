import type { ApiErrorCode } from "../types/api";

export class ApiError extends Error {
  code: ApiErrorCode;
  status: number;

  constructor(code: ApiErrorCode, message: string, status: number) {
    super(message);
    this.name = "ApiError";
    this.code = code;
    this.status = status;
  }
}

export async function parseErrorAndThrow(resp: Response): Promise<never> {
  const body = await resp.json().catch(() => null);
  const code: ApiErrorCode = body?.error?.code ?? "UNKNOWN";
  const message: string = body?.error?.message ?? `Ошибка запроса (${resp.status})`;
  throw new ApiError(code, message, resp.status);
}
