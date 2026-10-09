import { api } from "./client";
import type { Brand } from "@/lib/types";

export const brandsApi = {
  list: () => api.get<Brand[]>("/api/brands"),
};
