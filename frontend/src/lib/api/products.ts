import { api } from "./client";
import type { Category, Paginated, Product, Review } from "@/lib/types";

export interface ProductQuery {
  q?: string;
  category?: string;
  min?: number;
  max?: number;
  sort?: "newest" | "price_asc" | "price_desc" | "rating";
  page?: number;
  limit?: number;
}

export const productsApi = {
  list: (q: ProductQuery = {}) =>
    api.get<Paginated<Product>>("/api/products", { query: q as Record<string, string | number>, auth: false }),
  get: (id: string) => api.get<Product>(`/api/products/${id}`, { auth: false }),
  create: (data: Partial<Product>) => api.post<Product>("/api/products", data),
  update: (id: string, data: Partial<Product>) => api.put<Product>(`/api/products/${id}`, data),
  remove: (id: string) => api.del<void>(`/api/products/${id}`),
  reviews: (id: string) => api.get<Review[]>(`/api/products/${id}/reviews`, { auth: false }),
  addReview: (id: string, data: { rating: number; comment: string }) =>
    api.post<Review>(`/api/products/${id}/reviews`, data),
};

export const categoriesApi = {
  list: () => api.get<Category[]>("/api/categories", { auth: false }),
};
