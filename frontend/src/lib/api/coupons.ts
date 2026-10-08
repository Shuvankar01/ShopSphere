import { api } from "./client";
import { num, numOrNull } from "./normalize";
import type { Coupon } from "@/lib/types";

export interface CouponInput {
  code?: string;
  discount_type?: "percent" | "fixed";
  discount_value?: number;
  min_order_amount?: number | null;
  max_uses?: number | null;
  is_active?: boolean;
}

export function mapCoupon(c: Coupon): Coupon {
  return {
    ...c,
    discount_value: num(c.discount_value) ?? 0,
    min_order_amount: numOrNull(c.min_order_amount),
  };
}

export const couponsApi = {
  list: () => api.get<Coupon[]>("/api/coupons").then((items) => items.map(mapCoupon)),
  create: (data: CouponInput) => api.post<Coupon>("/api/coupons", data).then(mapCoupon),
  update: (id: string, data: CouponInput) =>
    api.put<Coupon>(`/api/coupons/${id}`, data).then(mapCoupon),
  deactivate: (id: string) => api.del<void>(`/api/coupons/${id}`),
};
