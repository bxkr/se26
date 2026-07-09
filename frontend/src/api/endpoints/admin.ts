import { apiDelete, apiGet, apiPatch, apiPost } from "../client";
import type {
  AdminUser,
  CreateUserRequest,
  ResetPasswordRequest,
  UpdateUserRequest,
} from "../../types/admin";

export function listUsers(): Promise<AdminUser[]> {
  return apiGet("/admin/users");
}

export function createUser(body: CreateUserRequest): Promise<AdminUser> {
  return apiPost("/admin/users", body);
}

export function updateUser(id: string, body: UpdateUserRequest): Promise<AdminUser> {
  return apiPatch(`/admin/users/${id}`, body);
}

export function deleteUser(id: string): Promise<void> {
  return apiDelete(`/admin/users/${id}`);
}

export function resetPassword(id: string, body: ResetPasswordRequest): Promise<void> {
  return apiPost(`/admin/users/${id}/reset-password`, body);
}
