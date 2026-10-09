import { api } from "./client";
import type { Address, AddressInput } from "@/lib/types";

export const addressesApi = {
  list: () => api.get<Address[]>("/api/addresses"),
  create: (data: AddressInput) => api.post<Address>("/api/addresses", data),
  get: (id: string) => api.get<Address>(`/api/addresses/${id}`),
  update: (id: string, data: Partial<AddressInput>) =>
    api.put<Address>(`/api/addresses/${id}`, data),
  setDefault: (id: string) => api.put<Address>(`/api/addresses/${id}/default`, {}),
  remove: (id: string) => api.del<void>(`/api/addresses/${id}`),
};
