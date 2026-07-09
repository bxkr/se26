import type { Role } from "./auth";

export interface AdminUser {
  id: string;
  username: string;
  role: Role;
  is_active: boolean;
  created_at: string;
}

export interface CreateUserRequest {
  username: string;
  password: string;
  role: Role;
}

export interface UpdateUserRequest {
  role?: Role;
  is_active?: boolean;
}

export interface ResetPasswordRequest {
  new_password: string;
}
