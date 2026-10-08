export type Role = "customer" | "seller" | "admin";

export interface User {
  id: string;
  full_name: string;
  email: string;
  role: Role;
  is_active: boolean;
  created_at: string;
}

export interface Category {
  id: string;
  name: string;
  description?: string | null;
  parent_id?: string | null;
  is_active?: boolean;
}

export interface Brand {
  id: string;
  name: string;
  description?: string | null;
  logo_url?: string | null;
  is_active: boolean;
  created_at: string;
}

export interface ProductImage {
  id: string;
  product_id: string;
  url: string;
  alt_text?: string | null;
  sort_order: number;
}

export interface ProductVariant {
  id: string;
  product_id: string;
  sku: string;
  name: string;
  /** Decimal — serialized as a JSON string by pydantic; APIs normalize to number. */
  price_override?: number | null;
  stock: number;
  /** JSON string of key/value attributes (e.g. {"Size":"L","Color":"Red"}). */
  attributes?: string | null;
  is_active: boolean;
}

export interface Product {
  id: string;
  name: string;
  description: string;
  sku?: string | null;
  /** Decimal — serialized as a JSON string by pydantic; APIs normalize to number. */
  price: number;
  discount_price?: number | null;
  stock: number;
  image_url?: string | null;
  /** JSON string of key/value specifications. */
  specifications?: string | null;
  category_id: string;
  brand_id?: string | null;
  seller_id: string;
  is_active: boolean;
  created_at: string;
  rating?: number;
  review_count?: number;
  category?: Category | null;
  brand?: Brand | null;
  images: ProductImage[];
  variants: ProductVariant[];
}

export interface CartItem {
  id: string;
  product_id: string;
  product: Product;
  quantity: number;
  unit_price: number;
}

export interface Cart {
  id: string;
  user_id: string;
  items: CartItem[];
  subtotal: number;
  discount_amount: number;
  total: number;
  coupon_code?: string | null;
  item_count: number;
}

export type OrderStatus = "pending" | "confirmed" | "shipped" | "delivered" | "cancelled";
export type PaymentStatus = "pending" | "paid" | "failed" | "refunded";

export interface OrderItem {
  id: string;
  product_id: string;
  product_name: string;
  quantity: number;
  price: number;
}

export interface Order {
  id: string;
  user_id: string;
  items: OrderItem[];
  total_amount: number;
  order_status: OrderStatus;
  payment_status: PaymentStatus;
  payment_method: string;
  shipping_address: string;
  coupon_id?: string | null;
  discount_amount: number;
  created_at: string;
}

export interface Review {
  id: string;
  user_id: string;
  user_name: string;
  product_id: string;
  rating: number;
  comment: string;
  created_at: string;
}

export interface Coupon {
  id: string;
  code: string;
  discount_type: "percent" | "fixed";
  /** Decimal — serialized as a JSON string by pydantic; APIs normalize to number. */
  discount_value: number;
  min_order_amount?: number | null;
  max_uses?: number | null;
  used_count: number;
  starts_at?: string | null;
  ends_at?: string | null;
  is_active: boolean;
  created_at: string;
}

export interface Inventory {
  id: string;
  product_id: string;
  physical_stock: number;
  reserved_stock: number;
  available_stock: number;
  low_stock_threshold: number;
  is_low_stock: boolean;
  updated_at: string;
}

export interface LowStockItem {
  product_id: string;
  product_name: string;
  inventory: Inventory;
}

export interface WishlistItem {
  id: string;
  product_id: string;
  product: Product;
  created_at: string;
}

export interface Wishlist {
  id: string;
  user_id: string;
  items: WishlistItem[];
}

export interface AuthTokens {
  access_token: string;
  refresh_token: string;
  token_type: "bearer";
}

export interface AuthResponse extends AuthTokens {
  user: User;
}

export interface Paginated<T> {
  items: T[];
  total: number;
  page: number;
  limit: number;
}

export interface AdminStats {
  total_users: number;
  total_orders: number;
  total_products: number;
  /** Decimal — serialized as a JSON string by pydantic (e.g. "1234.50"). */
  revenue: string;
  recent_orders: Order[];
}
