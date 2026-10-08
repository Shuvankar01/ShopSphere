import { api } from "./client";
import type { Inventory, LowStockItem } from "@/lib/types";

export const inventoryApi = {
  /** Seller: their own products' stock levels. */
  mine: () => api.get<LowStockItem[]>("/api/inventory/mine"),
  /** Seller: products that are below their low-stock threshold. */
  lowStock: () => api.get<LowStockItem[]>("/api/inventory/low-stock"),
  getByProduct: (productId: string) => api.get<Inventory>(`/api/inventory/products/${productId}`),
  setStock: (productId: string, data: { physical_stock: number; low_stock_threshold?: number }) =>
    api.put<Inventory>(`/api/inventory/products/${productId}`, data),
  /** Seller: adjusts their own stock (or admin for any product). */
  adjust: (productId: string, data: { quantity: number; note?: string }) =>
    api.post<Inventory>(`/api/inventory/products/${productId}/adjust`, data),
};
