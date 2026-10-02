import { api } from "./client";
import type { Cart } from "@/lib/types";

export const cartApi = {
  get: () => api.get<Cart>("/api/cart"),
  add: (product_id: string, quantity: number) => api.post<Cart>("/api/cart/add", { product_id, quantity }),
  update: (product_id: string, quantity: number) => api.put<Cart>("/api/cart/update", { product_id, quantity }),
  remove: (product_id: string) => api.del<Cart>(`/api/cart/remove?product_id=${encodeURIComponent(product_id)}`),
};
