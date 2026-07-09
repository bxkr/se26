import { apiFetch, apiPost } from "../client";
import type { LoginRequest, LoginResponse, User } from "../../types/auth";
import { parseErrorAndThrow } from "../errors";

export function login(body: LoginRequest): Promise<User> {
  return apiPost<LoginResponse>("/auth/login", body).then((r) => r.user);
}

export async function logout(): Promise<void> {
  await apiFetch("/auth/logout", { method: "POST" });
}

export async function me(): Promise<User | null> {
  const resp = await apiFetch("/auth/me", { method: "GET" });
  if (resp.status === 401) return null;
  if (!resp.ok) return parseErrorAndThrow(resp);
  return (await resp.json()) as User;
}
