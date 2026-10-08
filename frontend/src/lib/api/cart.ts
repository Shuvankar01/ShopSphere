import { api } from "./client";
import { num, numOrNull } from "./normalize";
import { mapProduct } from "./products";
import type { Cart } from "@/lib/types";

/** Convert Decimal-string money fields from the wire into numbers. */
export function mapCart(c: Cart): Cart {
  return {
    ...c,
    items: (c.items ?? []).map((i) => ({
      ...i,
      unit_price: num(i.unit_price) ?? 0,
      product: mapProduct(i.product),
    })),
    subtotal: num(c.subtotal) ?? 0,
    discount_amount: num(c.discount_amount) ?? 0,
    total: num(c.total) ?? 0,
  };
}

export const cartApi = {
  get: () => api.get<Cart>("/api/cart").then(mapCart),
  add: (product_id: string, quantity: number) =>
    api.post<Cart>("/api/cart/add", { product_id, quantity }).then(mapCart),
  update: (product_id: string, quantity: number) =>
    api.put<Cart>("/api/cart/update", { product_id, quantity }).then(mapCart),
  remove: (product_id: string) =>
    api.del<Cart>(`/api/cart/remove?product_id=${encodeURIComponent(product_id)}`).then(mapCart),
  applyCoupon: (code: string) => api.post<Cart>("/api/cart/coupon", { code }).then(mapCart),
  removeCoupon: () => api.del<Cart>("/api/cart/coupon").then(mapCart),
};
