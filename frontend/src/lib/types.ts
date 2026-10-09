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

export type OrderStatus =
  | "pending"
  | "confirmed"
  | "processing"
  | "packed"
  | "shipped"
  | "out_for_delivery"
  | "delivered"
  | "cancelled";

export type PaymentStatus =
  | "pending"
  | "paid"
  | "failed"
  | "refunded"
  | "partially_refunded";

export type ShipmentStatus =
  | "pending"
  | "processing"
  | "packed"
  | "shipped"
  | "out_for_delivery"
  | "delivered"
  | "cancelled";

export interface OrderItem {
  id: string;
  product_id: string;
  product_name: string;
  quantity: number;
  price: number;
}

export interface OrderStatusHistoryEntry {
  from_status?: string | null;
  to_status: string;
  changed_by?: string | null;
  note?: string | null;
  created_at: string;
}

export interface Order {
  id: string;
  user_id: string;
  items: OrderItem[];
  subtotal: number;
  discount_amount: number;
  tax_amount: number;
  shipping_cost: number;
  total_amount: number;
  order_status: OrderStatus;
  payment_status: PaymentStatus;
  payment_method: string;
  shipping_method: string;
  shipping_address: string;
  shipping_address_snapshot?: string | null;
  tracking_number?: string | null;
  shipment_status: ShipmentStatus;
  coupon_id?: string | null;
  status_history: OrderStatusHistoryEntry[];
  created_at: string;
}

export interface ReviewImage {
  id: string;
  url: string;
  sort_order: number;
}

export interface Review {
  id: string;
  user_id: string;
  user_name: string;
  product_id: string;
  rating: number;
  comment: string;
  is_verified?: boolean;
  moderation_status?: "pending" | "approved" | "rejected";
  images?: ReviewImage[];
  created_at: string;
}

export interface Address {
  id: string;
  label: string;
  recipient_name: string;
  phone?: string | null;
  line1: string;
  line2?: string | null;
  city: string;
  state?: string | null;
  postal_code: string;
  country: string;
  is_default: boolean;
  is_active?: boolean;
  created_at?: string;
}

export interface AddressInput {
  label?: string;
  recipient_name: string;
  phone?: string;
  line1: string;
  line2?: string;
  city: string;
  state?: string;
  postal_code: string;
  country: string;
  is_default?: boolean;
}

export interface ShippingMethod {
  code: string;
  name: string;
  /** Decimal-string from the wire; APIs normalize to number. */
  charge: number;
  estimated_days_min: number;
  estimated_days_max: number;
  description: string;
}

/** Backend-authoritative pre-checkout totals (POST /api/orders/quote). */
export interface CheckoutQuote {
  subtotal: number;
  discount_amount: number;
  tax_amount: number;
  shipping_cost: number;
  total_amount: number;
  shipping_method: string;
  shipping_method_name: string;
  estimated_delivery: string;
  coupon_code?: string | null;
  currency: string;
}

export type PaymentTransactionStatus =
  | "pending"
  | "succeeded"
  | "failed"
  | "cancelled"
  | "refunded"
  | "partially_refunded";

export interface PaymentTransaction {
  id: string;
  order_id: string;
  amount: number;
  currency: string;
  provider: string;
  transaction_id: string;
  status: PaymentTransactionStatus;
  created_at: string;
}

export type RefundStatus = "pending" | "completed" | "failed" | "cancelled";

export interface Refund {
  id: string;
  payment_id: string;
  order_id: string;
  amount: number;
  status: RefundStatus;
  reason?: string | null;
  idempotency_key?: string | null;
  provider_reference?: string | null;
  created_at: string;
}

export type ReturnStatus =
  | "requested"
  | "approved"
  | "rejected"
  | "received"
  | "completed"
  | "cancelled";

export interface ReturnItem {
  id: string;
  order_item_id: string;
  quantity: number;
  reason?: string | null;
  created_at?: string;
}

export interface ReturnRequest {
  id: string;
  order_id: string;
  user_id: string;
  status: ReturnStatus;
  reason: string;
  items: ReturnItem[];
  created_at: string;
  updated_at?: string;
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
