import { api } from "./client";
import type { User } from "@/lib/types";

export const usersApi = {
  profile: () => api.get<User>("/api/users/profile"),
  updateProfile: (data: Partial<Pick<User, "full_name" | "email">>) =>
    api.put<User>("/api/users/profile", data),
};
