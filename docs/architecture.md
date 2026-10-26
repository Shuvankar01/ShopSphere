# Architecture

- Frontend: TanStack Start + React 19 + Vite + Tailwind v4 (SPA/SSR capable via TanStack Start)
- Backend: FastAPI REST API under `/api/*`
- DB: PostgreSQL (authoritative)
- Auth: JWT access tokens
- Money: Decimal
- Migrations: Alembic
- AI: provider abstraction with mock fallback
- Invoices: local generation
- Notifications: in-app only
- Demo payments: two-phase mock
