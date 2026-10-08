import { api } from "./client";
import { mapProduct } from "./products";
import type { Cart, Wishlist } from "@/lib/types";

export const wishlistApi = {
  get: () =>
    api.get<Wishlist>("/api/wishlist").then((w) => ({
      ...w,
      items: (w.items ?? []).map((i) => ({ ...i, product: mapProduct(i.product) })),
    })),
  add: (productId: string) => api.post<Wishlist>(`/api/wishlist/add`, { product_id: productId }),
  remove: (productId: string) => api.del<Wishlist>(`/api/wishlist/remove/${productId}`),
  moveToCart: (productId: string, quantity: number) =>
    api.post<Cart>(`/api/wishlist/move-to-cart`, { product_id: productId, quantity }),
};
