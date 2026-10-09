import { api } from "./client";
import type { Category } from "@/lib/types";

export const categoriesApi = {
  list: () => api.get<Category[]>("/api/categories"),
};
