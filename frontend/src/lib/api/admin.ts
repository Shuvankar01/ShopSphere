import { api } from "./client";
import type { AdminStats, Order, Product, User } from "@/lib/types";

export const adminApi = {
  dashboard: () => api.get<AdminStats>("/api/admin/dashboard"),
  users: () => api.get<User[]>("/api/admin/users"),
  orders: () => api.get<Order[]>("/api/admin/orders"),
  products: () => api.get<Product[]>("/api/admin/products"),
};
