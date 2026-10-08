# ShopSphere — Frontend

Production-grade React + TypeScript + Tailwind storefront for the **ShopSphere** e-commerce platform. This repo is **frontend only** — it talks to a separate Python/FastAPI backend over REST.

## Stack
- **TanStack Start** (React 19 + Vite) with file-based routing
- **TypeScript**, **Tailwind v4**, **shadcn/ui**
- **TanStack Query** for server state, **react-hook-form + Zod** for forms
- **JWT auth** (access + refresh) with automatic refresh on 401
- Role-based UI guards: `customer`, `seller`, `admin`

## Pages
| Surface  | Routes |
|----------|--------|
| Public   | `/`, `/products`, `/products/:id`, `/login`, `/register` |
| Customer | `/dashboard`, `/cart`, `/checkout`, `/orders`, `/orders/:id`, `/wishlist`, `/profile` |
| Seller   | `/seller/products` (CRUD listings, SKU/brand/specs, variants, image upload), `/seller/inventory` (stock tracking) |
| Admin    | `/admin`, `/admin/users`, `/admin/orders`, `/admin/products`, `/admin/coupons` |

## Setup

```bash
npm install
cp .env.example .env       # set VITE_API_BASE_URL
npm run dev
```

Open http://localhost:5173.

### Environment
| Var | Description |
|-----|-------------|
| `VITE_API_BASE_URL` | Base URL of your FastAPI backend, e.g. `http://localhost:8000` |

## Expected backend contract

The frontend talks to these endpoints (all JSON, JWT bearer auth except where noted). Match these in your FastAPI app — see the type contracts in `src/lib/types.ts`.

### Auth
- `POST /api/auth/register` → `{ access_token, refresh_token, token_type:"bearer", user }` (role: `customer`|`seller` only)
- `POST /api/auth/login` → same shape (rate-limited: 429 after 5 failed attempts/min per IP+email)
- `POST /api/auth/refresh` body `{ refresh_token }` → `{ access_token, refresh_token? }`
- `POST /api/auth/logout` (auth) → `204` — client discards its tokens; JWTs are stateless
- `POST /api/auth/change-password` (auth) body `{ current_password, new_password }` → `204`

### Users
- `GET /api/users/profile` → `User`
- `PUT /api/users/profile` body `{ full_name, email }` → `User`

### Products
- `GET /api/products?q=&category=&brand_id=&min=&max=&min_rating=&in_stock=&has_discount=&sort=&seller_id=&page=&limit=&include_inactive=` → `Paginated<Product>` (public: active only; `include_inactive=true` requires seller/admin auth and is scoped server-side). `q` also matches SKU; `category` includes descendant categories; `sort` = `newest`|`price_asc`|`price_desc`|`rating`
- `GET /api/products/:id` → `Product` (404 for inactive products unless owner/admin)
- `GET /api/products/:id/related?limit=` → `Product[]` (same category, same brand first, max 24)
- `POST/PUT/DELETE /api/products[/:id]` (seller/admin; delete is a soft deactivation)
- `GET /api/products/:id/reviews` → `Review[]`
- `POST /api/products/:id/reviews` body `{ rating, comment }` → `Review`
- `GET /api/products/search/suggestions?q=` → `string[]`
- Images (seller/admin, own product):
  - `POST /api/products/:id/images/upload` — multipart `file` (PNG/JPEG/WebP/GIF, ≤ 5 MB) → `ProductImage`
  - `DELETE /api/products/:id/images/:image_id` → `204`
- Variants (seller/admin, own product):
  - `POST /api/products/:id/variants` body `{ sku, name, price_override?, stock, attributes? }` → `ProductVariant` (duplicate SKU → 409)
  - `PUT /api/products/:id/variants/:variant_id` → `ProductVariant`
  - `DELETE /api/products/:id/variants/:variant_id` → `204`
  - When active variants exist, `product.stock` = sum of active variant stock (editing `product.stock` directly is then blocked)

> All monetary/rating fields (`price`, `discount_price`, `rating`, `subtotal`, `discount_amount`, `total`, `unit_price`, `total_amount`, `discount_value`, `min_order_amount`, `price_override`) are serialized as **JSON strings** by the backend and normalized to numbers by the API layer (`src/lib/api/normalize.ts`). `specifications` is a JSON-object string (`{"Color":"Black"}`).

### Categories
- `GET /api/categories` → `Category[]` (`parent_id` supports nesting; category list includes descendants in product filters)
- `POST /api/categories` (admin) body `{ name, description?, parent_id? }` → `Category` (cycle-creating parent → 400/409)
- `PUT /api/categories/:id` (admin) body `{ name?, description?, parent_id?, is_active? }` → `Category`

### Brands
- `GET /api/brands` → `Brand[]`
- `POST /api/brands` (admin) body `{ name, description?, logo_url? }` → `Brand`
- `PUT /api/brands/:id` (admin) body `{ name?, description?, logo_url?, is_active? }` → `Brand`

### Cart
- `GET /api/cart` → `Cart` (`{ id, user_id, items[], subtotal, discount_amount, total, coupon_code?, item_count }`)
- `POST /api/cart/add` body `{ product_id, quantity }` → `Cart`
- `PUT /api/cart/update` body `{ product_id, quantity }` → `Cart`
- `DELETE /api/cart/remove?product_id=…` → `Cart`
- `POST /api/cart/coupon` body `{ code }` → `Cart` (applies coupon; discount re-derived on every cart change)
- `DELETE /api/cart/coupon` → `Cart` (removes coupon)

### Coupons
- `GET /api/coupons` → `Coupon[]` (admin)
- `POST /api/coupons` (admin) body `{ code, discount_type: percent|fixed, discount_value, min_order_amount?, max_uses?, starts_at?, ends_at?, is_active? }` → `Coupon`
- `PUT /api/coupons/:id` (admin) `CouponUpdate` → `Coupon`
- `DELETE /api/coupons/:id` (admin) → `204` (deactivates)
- Usage is recorded at checkout (bound to the order), max once per user; the discount flows into `order.discount_amount` / `order.total_amount`

### Inventory
- `GET /api/inventory/mine` → `LowStockItem[]` (seller: own products; admin: all)
- `GET /api/inventory/low-stock?limit=` → `LowStockItem[]` (below threshold)
- `GET /api/inventory/products/:product_id` → `Inventory` (`{ physical_stock, reserved_stock, available_stock, low_stock_threshold, is_low_stock }`)
- `PUT /api/inventory/products/:product_id` body `{ physical_stock, low_stock_threshold? }` → `Inventory` (seller, own product)
- `POST /api/inventory/products/:product_id/adjust` body `{ quantity, note? }` → `Inventory` (seller: ±own stock; admin: any; negative result → 400)

### Wishlist
- `GET /api/wishlist` → `Wishlist` (`{ id, user_id, items[] }`)
- `POST /api/wishlist/add` body `{ product_id }` → `Wishlist` (no duplicates; inactive product → 400)
- `DELETE /api/wishlist/remove/:product_id` → `Wishlist`
- `POST /api/wishlist/move-to-cart` body `{ product_id, quantity? }` → `Cart` (adds to cart; respects the cart's applied coupon; inactive product → 400)

### Orders
- `POST /api/orders/create` body `{ shipping_address, payment_method }` → `Order` (card/paypal/cod/…; 201; atomic stock reserve/coupon record)
- `GET /api/orders` → `Order[]` (own orders only)
- `GET /api/orders/:id` → `Order` (owner or admin; 404 otherwise — no existence leak)
- `PUT /api/orders/:id/status` body `{ status }` → `Order` (admin only)

### Payments
- `POST /api/payment/create` body `{ order_id, payment_method }` → `{ transaction_id, status, redirect_url? }` (owner only; 404 unknown/foreign order, 409 already paid/cancelled, 422 invalid method)

### Admin
- `GET /api/admin/dashboard` → `AdminStats`
- `GET /api/admin/users` → `User[]`
- `GET /api/admin/orders` → `Order[]`
- `GET /api/admin/products` → `Product[]`
- Coupon/brand/category management live under `POST/PUT/DELETE /api/coupons`, `/api/brands`, `/api/categories` (admin-only, see above)

### CORS
Your FastAPI backend must allow this frontend's origin and `Authorization` header. Add `fastapi.middleware.cors.CORSMiddleware` with `allow_credentials=True`, `allow_methods=["*"]`, `allow_headers=["*"]`.

## Project layout
```
src/
  routes/                       # File-based pages (TanStack Router)
  components/
    layout/    Header, Footer, AppShell
    products/  ProductCard, ProductGrid
    ui/        shadcn primitives
  lib/
    api/       Typed REST modules (auth, products, cart, coupons, inventory, wishlist, orders, payments, users, admin, normalize)
    auth/      AuthContext, RequireAuth guard, tokenStore
    types.ts   Shared TypeScript contracts
    schemas.ts Zod form schemas
    format.ts  Currency / date helpers
  hooks/       useCart
```

## Auth flow
1. `login` / `register` stores `access_token` + `refresh_token` in `localStorage`.
2. Every API call attaches `Authorization: Bearer <access>`.
3. On `401`, the client transparently calls `/api/auth/refresh` once and retries. If refresh fails, the user is signed out.
4. Role-gated routes use `<RequireAuth roles={['admin']}>`.

## Building the FastAPI backend
The backend lives in this repo under `backend/` (FastAPI + SQLAlchemy + Alembic + PostgreSQL + bcrypt + JWT). Match the endpoints above and the types in `src/lib/types.ts`. With CORS enabled and `VITE_API_BASE_URL` set, the frontend is plug-and-play.
