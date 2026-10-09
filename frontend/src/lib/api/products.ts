import { api } from "./client";
import { num, numOrNull } from "./normalize";
import type {
  Brand,
  Category,
  Paginated,
  Product,
  ProductImage,
  ProductVariant,
  Review,
} from "@/lib/types";

export interface ProductQuery {
  q?: string;
  category?: string;
  brand_id?: string;
  min?: number;
  max?: number;
  min_rating?: number;
  in_stock?: boolean;
  has_discount?: boolean;
  sort?: "newest" | "price_asc" | "price_desc" | "rating";
  seller_id?: string;
  page?: number;
  limit?: number;
  include_inactive?: boolean;
}

export function mapProduct(p: any): Product {
  return {
    ...p,
    price: num(p.price) ?? 0,
    discount_price: numOrNull(p.discount_price),
    rating: num(p.rating),
    variants: (p.variants ?? []).map((v: any) => ({
      ...v,
      price_override: numOrNull(v.price_override),
      attributes: typeof v.attributes === "string" ? v.attributes : JSON.stringify(v.attributes ?? {}),
    })),
  };
}

export function mapReview(r: any): Review {
  return {
    ...r,
    rating: Number(r.rating) || 0,
    images: r.images ?? [],
    is_verified: Boolean(r.is_verified),
  };
}

export const productsApi = {
  list: (query: ProductQuery = {}) =>
    api
      .get<Paginated<Product>>("/api/products", { query: query as Record<string, any> })
      .then((res) => ({ ...res, items: res.items.map(mapProduct) })),
  get: (id: string) => api.get<Product>(`/api/products/${id}`).then(mapProduct),
  create: (data: Partial<Product>) => api.post<Product>("/api/products", data).then(mapProduct),
  update: (id: string, data: Partial<Product>) => api.put<Product>(`/api/products/${id}`, data).then(mapProduct),
  remove: (id: string) => api.del<void>(`/api/products/${id}`),
  getReviews: (id: string) => api.get<Review[]>(`/api/products/${id}/reviews`).then((items) => items.map(mapReview)),
  reviews: (id: string) => api.get<Review[]>(`/api/products/${id}/reviews`).then((items) => items.map(mapReview)),
  related: (id: string) => api.get<Paginated<Product>>(`/api/products/${id}/related`).then((res) => ({ ...res, items: res.items.map(mapProduct) })),
  addReview: (id: string, data: { rating: number; comment: string; image_urls?: string[] }) =>
    api.post<Review>(`/api/products/${id}/reviews`, data).then(mapReview),
  uploadImage: (id: string, file: File) => {
    const form = new FormData();
    form.append("file", file);
    return api.post(`/api/products/${id}/images`, form);
  },
  deleteImage: (id: string, imageId: string) =>
    api.del(`/api/products/${id}/images/${imageId}`),
  createVariant: (id: string, data: any) =>
    api.post(`/api/products/${id}/variants`, data),
  updateVariant: (id: string, variantId: string, data: any) =>
    api.put(`/api/products/${id}/variants/${variantId}`, data),
  deleteVariant: (id: string, variantId: string) =>
    api.del(`/api/products/${id}/variants/${variantId}`),
};
