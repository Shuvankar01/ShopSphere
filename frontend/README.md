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
| Customer | `/dashboard`, `/cart`, `/checkout`, `/orders`, `/orders/:id`, `/profile` |
| Seller   | `/seller/products` (CRUD listings) |
| Admin    | `/admin`, `/admin/users`, `/admin/orders`, `/admin/products` |

## Setup

```bash
num install
cp .env.example .env       # set VITE_API_BASE_URL
num run dev
```

Open http://localhost:8080.

### Environment
| Var | Description |
|-----|-------------|
| `VITE_API_BASE_URL` | Base URL of your FastAPI backend, e.g. `http://localhost:8000` |

## Expected backend contract

The frontend talks to these endpoints (all JSON, JWT bearer auth except where noted). Match these in your FastAPI app — see the type contracts in `src/lib/types.ts`.

### Auth
- `POST /api/auth/register` → `{ access_token, refresh_token, token_type:"bearer", user }`
- `POST /api/auth/login` → same shape
- `POST /api/auth/refresh` body `{ refresh_token }` → `{ access_token, refresh_token? }`

### Users
- `GET /api/users/profile` → `User`
- `PUT /api/users/profile` body `{ full_name, email }` → `User`

### Products
- `GET /api/products?q=&category=&min=&max=&sort=&page=&limit=` → `Paginated<Product>`
- `GET /api/products/:id` → `Product`
- `POST/PUT/DELETE /api/products[/:id]` (seller/admin)
- `GET /api/products/:id/reviews` → `Review[]`
- `POST /api/products/:id/reviews` body `{ rating, comment }` → `Review`

### Categories
- `GET /api/categories` → `Category[]`

### Cart
- `GET /api/cart` → `Cart`
- `POST /api/cart/add` body `{ product_id, quantity }` → `Cart`
- `PUT /api/cart/update` body `{ product_id, quantity }` → `Cart`
- `DELETE /api/cart/remove?product_id=…` → `Cart`

### Orders
- `POST /api/orders/create` body `{ shipping_address, payment_method }` → `Order`
- `GET /api/orders` → `Order[]`
- `GET /api/orders/:id` → `Order`
- `PUT /api/orders/:id/status` body `{ status }` → `Order` (admin/seller)

### Payments
- `POST /api/payment/create` body `{ order_id, payment_method }` → `{ transaction_id, status, redirect_url? }`
- `POST /api/payment/webhook` (server-to-server, no auth)

### Admin
- `GET /api/admin/dashboard` → `AdminStats`
- `GET /api/admin/users` → `User[]`
- `GET /api/admin/orders` → `Order[]`
- `GET /api/admin/products` → `Product[]`

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
    api/       Typed REST modules (auth, products, cart, orders, payments, users, admin)
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
This repo intentionally excludes Python. Build it separately following the spec in your project brief (FastAPI + SQLAlchemy + Alembic + PostgreSQL + bcrypt + JWT). Match the endpoints above and the types in `src/lib/types.ts`. With CORS enabled and `VITE_API_BASE_URL` set, the frontend is plug-and-play.
