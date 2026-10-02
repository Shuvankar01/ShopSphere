import { api } from "./client";
import type { Order } from "@/lib/types";

export const ordersApi = {
  create: (data: { shipping_address: string; payment_method: string }) =>
    api.post<Order>("/api/orders/create", data),
  list: () => api.get<Order[]>("/api/orders"),
  get: (id: string) => api.get<Order>(`/api/orders/${id}`),
  updateStatus: (id: string, status: Order["order_status"]) =>
    api.put<Order>(`/api/orders/${id}/status`, { status }),
};
