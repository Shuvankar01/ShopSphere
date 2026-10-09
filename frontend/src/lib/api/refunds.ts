import { api } from "./client";
import { num } from "./normalize";
import type { Refund } from "@/lib/types";

export function mapRefund(r: any): Refund {
  return {
    ...r,
    amount: num(r.amount) ?? 0,
  };
}

export const refundsApi = {
  create: (data: { order_id: string; amount: number | string; reason?: string; idempotency_key?: string }) =>
    api.post<Refund>("/api/refunds", data).then(mapRefund),
  list: (order_id?: string) =>
    api.get<Refund[]>(`/api/refunds${order_id ? `?order_id=${order_id}` : ""}`).then((items) => items.map(mapRefund)),
  get: (id: string) => api.get<Refund>(`/api/refunds/${id}`).then(mapRefund),
};
