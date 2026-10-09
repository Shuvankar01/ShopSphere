import { api } from "./client";
import { num } from "./normalize";
import type { CheckoutQuote, Order } from "@/lib/types";

export function mapOrder(o: any): Order {
  return {
    ...o,
    items: (o.items ?? []).map((i: any) => ({ ...i, price: num(i.price) ?? 0 })),
    subtotal: num(o.subtotal) ?? num(o.total_amount) ?? 0,
    discount_amount: num(o.discount_amount) ?? 0,
    tax_amount: num(o.tax_amount) ?? 0,
    shipping_cost: num(o.shipping_cost) ?? 0,
    total_amount: num(o.total_amount) ?? 0,
    tracking_number: o.tracking_number ?? null,
  };
}

export const ordersApi = {
  create: (data: { shipping_address?: string; shipping_address_id?: string; shipping_method?: string; payment_method?: string }) =>
    api.post<Order>("/api/orders/create", data).then(mapOrder),
  quote: (shipping_method?: string) =>
    api
      .post<CheckoutQuote>("/api/orders/quote", { shipping_method: shipping_method || "standard" })
      .then((q) => ({
        ...q,
        subtotal: num(q.subtotal) ?? 0,
        discount_amount: num(q.discount_amount) ?? 0,
        tax_amount: num(q.tax_amount) ?? 0,
        shipping_cost: num(q.shipping_cost) ?? 0,
        total_amount: num(q.total_amount) ?? 0,
      })),
  list: () => api.get<Order[]>("/api/orders").then((items) => items.map(mapOrder)),
  get: (id: string) => api.get<Order>(`/api/orders/${id}`).then(mapOrder),
  updateStatus: (id: string, status: Order["order_status"]) =>
    api.put<Order>(`/api/orders/${id}/status`, { status }).then(mapOrder),
  cancel: (id: string, reason?: string) =>
    api.post<Order>(`/api/orders/${id}/cancel`, reason ? { reason } : {}).then(mapOrder),
};
