# ShopSphere

Full-stack e-commerce platform built with FastAPI (backend) and TanStack Start + React 19 + Vite + Tailwind CSS v4 (frontend). PostgreSQL is required for all environments (no SQLite fallback).

## Features
- Authentication (email/password; no OTP/email verification)
- Products, categories, brands, variants, images
- Cart, wishlist
- Checkout with address, shipping, coupons, tax
- DEMO two-phase payments (mock provider)
- Orders, status history, returns, refunds (demo)
- Reviews with moderation
- Admin dashboard and management
- Inventory with movement history
- Notifications (in-app only)
- Invoices (local HTML/PDF fallback)
- AI (mock when key unavailable)
- Recommendations (rule-based)
- SEO/PWA basics

## Tech Stack
- Backend: FastAPI, SQLAlchemy, Alembic, Pydantic v2, psycopg
- Frontend: TanStack Start, React 19, TypeScript, Vite, Tailwind CSS v4, shadcn/ui, TanStack Query, React Hook Form, Zod
- Database: PostgreSQL
- Testing: pytest

## Quickstart (Local)

Backend:
```bash
cd backend
pip install -r requirements.txt
# set DATABASE_URL
alembic upgrade head
uvicorn app.main:app --reload --port 8000
```

Frontend:
```bash
cd frontend
npm ci
npm run dev
```

## Docker
```bash
docker compose up --build
```

## Testing
```bash
cd backend
python -m pytest -q
cd frontend
npx tsc --noEmit && npm run build
```

See `docs/` for architecture, API, security, development, deployment details.
