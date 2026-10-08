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
  /** Staff only (401/403 otherwise): include unpublished (inactive) products. */
  include_inactive?: boolean;
}

/** Convert Decimal-string fields from the wire into numbers. */
export function mapProduct(p: Product): Product {
  return {
    ...p,
    price: num(p.price) ?? 0,
    discount_price: numOrNull(p.discount_price),
    rating: num(p.rating),
    variants: (p.variants ?? []).map((v) => ({
      ...v,
      price_override: numOrNull(v.price_override),
    })),
  };
}

const mapImages = (images: ProductImage[]): ProductImage[] => (images ?? []).map((i) => ({ ...i }));

export const productsApi = {
  list: (q: ProductQuery = {}, opts: { auth?: boolean } = {}) =>
    api
      .get<Paginated<Product>>("/api/products", {
        query: q as Record<string, string | number | boolean>,
        auth: opts.auth ?? false,
      })
      .then((res) => ({ ...res, items: res.items.map(mapProduct) })),
  get: (id: string) =>
    api
      .get<Product>(`/api/products/${id}`, { auth: false })
      .then((p) => ({ ...mapProduct(p), images: mapImages(p.images) })),
  related: (id: string) =>
    api
      .get<Product[]>(`/api/products/${id}/related`, { auth: false })
      .then((items) => items.map(mapProduct)),
  create: (data: Partial<Product>) => api.post<Product>("/api/products", data).then(mapProduct),
  update: (id: string, data: Partial<Product>) =>
    api.put<Product>(`/api/products/${id}`, data).then(mapProduct),
  remove: (id: string) => api.del<void>(`/api/products/${id}`),
  uploadImage: (id: string, file: File) => {
    const fd = new FormData();
    fd.append("file", file);
    return api.post<ProductImage>(`/api/products/${id}/images/upload`, fd);
  },
  deleteImage: (id: string, imageId: string) =>
    api.del<void>(`/api/products/${id}/images/${imageId}`),
  createVariant: (id: string, data: Partial<ProductVariant>) =>
    api.post<ProductVariant>(`/api/products/${id}/variants`, data).then((v) => ({
      ...v,
      price_override: numOrNull(v.price_override),
    })),
  updateVariant: (id: string, variantId: string, data: Partial<ProductVariant>) =>
    api.put<ProductVariant>(`/api/products/${id}/variants/${variantId}`, data).then((v) => ({
      ...v,
      price_override: numOrNull(v.price_override),
    })),
  deleteVariant: (id: string, variantId: string) =>
    api.del<void>(`/api/products/${id}/variants/${variantId}`),
  reviews: (id: string) => api.get<Review[]>(`/api/products/${id}/reviews`, { auth: false }),
  addReview: (id: string, data: { rating: number; comment: string }) =>
    api.post<Review>(`/api/products/${id}/reviews`, data),
};

export const categoriesApi = {
  list: () => api.get<Category[]>("/api/categories", { auth: false }),
};

export const brandsApi = {
  list: () => api.get<Brand[]>("/api/brands", { auth: false }),
  create: (data: { name: string; description?: string; logo_url?: string }) =>
    api.post<Brand>("/api/brands", data),
  update: (
    id: string,
    data: { name?: string; description?: string; logo_url?: string; is_active?: boolean },
  ) => api.put<Brand>(`/api/brands/${id}`, data),
};
