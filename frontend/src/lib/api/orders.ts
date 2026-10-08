import { api } from "./client";
import { num } from "./normalize";
import type { Order } from "@/lib/types";

export function mapOrder(o: Order): Order {
  return {
    ...o,
    items: (o.items ?? []).map((i) => ({ ...i, price: num(i.price) ?? 0 })),
    total_amount: num(o.total_amount) ?? 0,
    discount_amount: num(o.discount_amount) ?? 0,
  };
}

export const ordersApi = {
  create: (data: { shipping_address: string; payment_method: string }) =>
    api.post<Order>("/api/orders/create", data).then(mapOrder),
  list: () => api.get<Order[]>("/api/orders").then((items) => items.map(mapOrder)),
  get: (id: string) => api.get<Order>(`/api/orders/${id}`).then(mapOrder),
  updateStatus: (id: string, status: Order["order_status"]) =>
    api.put<Order>(`/api/orders/${id}/status`, { status }).then(mapOrder),
};
