# ShopSphere

ShopSphere is a full-stack e-commerce application with a FastAPI backend and a React/TypeScript frontend.

## Project Structure

- `backend/` - FastAPI REST API with SQLAlchemy, Alembic migrations, and pytest suite.
- `frontend/` - React frontend built with TanStack Router, TypeScript, and Vite.

## Getting Started

### Backend
1. `cd backend`
2. Set up virtual environment `.venv`
3. Install dependencies: `pip install -r requirements.txt`
4. Run migrations: `alembic upgrade head`
5. Seed database: `python scripts/seed.py`
6. Start server: `uvicorn app.utils.main:app --reload`

### Frontend
1. `cd frontend`
2. Install dependencies: `npm install`
3. Start dev server: `npm run dev`