import { api } from "./client";
import type { ReturnRequest, ReturnStatus } from "@/lib/types";

export const returnsApi = {
  create: (data: { order_id: string; reason: string; items: { order_item_id: string; quantity: number; reason?: string }[] }) =>
    api.post<ReturnRequest>("/api/returns", data),
  listMine: () => api.get<ReturnRequest[]>("/api/returns"),
  get: (id: string) => api.get<ReturnRequest>(`/api/returns/${id}`),
  cancel: (id: string) => api.post<ReturnRequest>(`/api/returns/${id}/cancel`, {}),
};

export const adminReturnsApi = {
  list: (order_id?: string) =>
    api.get<ReturnRequest[]>(`/api/admin/returns${order_id ? `?order_id=${order_id}` : ""}`),
  get: (id: string) => api.get<ReturnRequest>(`/api/admin/returns/${id}`),
  approve: (id: string, reason?: string) => api.post<ReturnRequest>(`/api/admin/returns/${id}/approve`, { reason }),
  reject: (id: string, reason?: string) => api.post<ReturnRequest>(`/api/admin/returns/${id}/reject`, { reason }),
  receive: (id: string) => api.post<ReturnRequest>(`/api/admin/returns/${id}/receive`, {}),
  complete: (id: string) => api.post<ReturnRequest>(`/api/admin/returns/${id}/complete`, {}),
  refund: (id: string) => api.post<{ refund: any; return_status: ReturnStatus }>(`/api/admin/returns/${id}/refund`, {}),
};
