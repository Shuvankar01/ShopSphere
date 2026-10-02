import { api } from "./client";
import type { AuthResponse, User } from "@/lib/types";

export const authApi = {
  register: (data: { full_name: string; email: string; password: string; role?: "customer" | "seller" }) =>
    api.post<AuthResponse>("/api/auth/register", data, { auth: false }),
  login: (data: { email: string; password: string }) =>
    api.post<AuthResponse>("/api/auth/login", data, { auth: false }),
  me: () => api.get<User>("/api/users/profile"),
};
