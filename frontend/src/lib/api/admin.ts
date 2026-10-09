import { api } from "./client";
import { mapOrder } from "./orders";
import { mapProduct } from "./products";
import { num } from "./normalize";
import type {
  AdminStats,
  Coupon,
  Order,
  Product,
  Review,
  User,
} from "@/lib/types";

export function mapAdminStats(s: any): AdminStats {
  return {
    ...s,
    revenue: typeof s.revenue === "string" || typeof s.revenue === "number" ? String(s.revenue) : "0",
    recent_orders: (s.recent_orders ?? []).map(mapOrder),
  };
}

export const adminApi = {
  stats: () => api.get<AdminStats>("/api/admin/stats").then(mapAdminStats),
  dashboard: () => api.get<AdminStats>("/api/admin/stats").then(mapAdminStats),
  users: () => api.get<User[]>("/api/admin/users"),
  toggleUser: (id: string) => api.put<User>(`/api/admin/users/${id}/toggle`, {}),
  orders: () => api.get<Order[]>("/api/admin/orders").then((items) => items.map(mapOrder)),
  updateOrderStatus: (id: string, status: Order["order_status"], reason?: string) =>
    api.put<Order>(`/api/admin/orders/${id}/status`, { status, reason }).then(mapOrder),
  products: () => api.get<Product[]>("/api/admin/products").then((items) => items.map(mapProduct)),
  toggleProduct: (id: string) => api.put<Product>(`/api/admin/products/${id}/toggle`, {}).then(mapProduct),
  coupons: () => api.get<Coupon[]>("/api/admin/coupons"),
  createCoupon: (data: Partial<Coupon> & { code: string; discount_type: "percent" | "fixed"; discount_value: number }) =>
    api.post<Coupon>("/api/admin/coupons", data),
  reviews: (status?: string) =>
    api.get<Review[]>(`/api/admin/reviews${status ? `?status=${status}` : ""}`),
  moderateReview: (id: string, action: "approve" | "reject") =>
    api.post<Review>(`/api/admin/reviews/${id}/moderate`, { action }),
};
