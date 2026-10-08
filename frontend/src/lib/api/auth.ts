import { api } from "./client";
import type { AuthResponse, User } from "@/lib/types";

export const authApi = {
  register: (data: {
    full_name: string;
    email: string;
    password: string;
    role?: "customer" | "seller";
  }) => api.post<AuthResponse>("/api/auth/register", data, { auth: false }),
  login: (data: { email: string; password: string }) =>
    api.post<AuthResponse>("/api/auth/login", data, { auth: false }),
  logout: () => api.post<void>("/api/auth/logout"),
  changePassword: (data: { current_password: string; new_password: string }) =>
    api.post<void>("/api/auth/change-password", data),
  me: () => api.get<User>("/api/users/profile"),
};
