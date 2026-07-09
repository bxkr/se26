import { apiDelete, apiGet, apiPatch, apiPost } from "../client";
import type {
  AdminUser,
  CreateUserRequest,
  ResetPasswordRequest,
  UpdateUserRequest,
} from "../../types/admin";

export async function listUsers(): Promise<AdminUser[]> {
  const { users } = await apiGet<{ users: AdminUser[] }>("/admin/users");
  return users;
}

export async function createUser(body: CreateUserRequest): Promise<AdminUser> {
  const { user } = await apiPost<{ user: AdminUser }>("/admin/users", body);
  return user;
}

export async function updateUser(id: string, body: UpdateUserRequest): Promise<AdminUser> {
  const { user } = await apiPatch<{ user: AdminUser }>(`/admin/users/${id}`, body);
  return user;
}

export function deleteUser(id: string): Promise<void> {
  return apiDelete(`/admin/users/${id}`);
}

export function resetPassword(id: string, body: ResetPasswordRequest): Promise<void> {
  return apiPost(`/admin/users/${id}/reset-password`, body);
}
