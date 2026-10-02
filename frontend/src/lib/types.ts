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
}

export interface Product {
  id: string;
  name: string;
  description: string;
  price: number;
  discount_price?: number | null;
  stock: number;
  image_url?: string | null;
  category_id: string;
  category?: Category | null;
  seller_id: string;
  created_at: string;
  rating?: number;
  review_count?: number;
}

export interface CartItem {
  id: string;
  product_id: string;
  product: Product;
  quantity: number;
}

export interface Cart {
  id: string;
  user_id: string;
  items: CartItem[];
  subtotal: number;
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
  shipping_address: string;
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
  revenue: number;
  recent_orders: Order[];
}
