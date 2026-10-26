# Development

Backend: cd backend; pip install -r requirements.txt; alembic upgrade head; uvicorn app.main:app --reload --port 8000. Tests: python -m pytest.
Frontend: cd frontend; npm ci; npm run dev. Typecheck: npx tsc --noEmit. Build: npm run build.
Lint/format as configured.
