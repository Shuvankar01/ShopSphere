# ShopSphere API Backend

This is the FastAPI backend for the ShopSphere e-commerce application. It provides a robust, fully-typed API backed by PostgreSQL and SQLAlchemy, adhering to modern clean architecture principles.

## Features

- **FastAPI Framework**: High performance, fully asynchronous capability, automatic Swagger documentation.
- **PostgreSQL Database**: Data persistence using the modern `psycopg` driver.
- **SQLAlchemy ORM**: Clean data models and repository pattern.
- **Alembic**: Database schema migrations.
- **JWT Authentication**: Secure role-based access control (Customer, Seller, Admin).
- **Comprehensive Testing**: Pytest setup with in-memory SQLite for fast testing.
- **Pre-commit Hooks**: Enforces code quality with Black and Ruff.

## Project Structure

```
backend/
├── alembic/              # Database migration scripts
├── app/
│   ├── config/           # Application configuration
│   ├── core/             # Security, logging, exceptions
│   ├── database/         # Database connection and session
│   ├── dependencies/     # FastAPI dependencies (auth)
│   ├── middleware/       # Custom middlewares
│   ├── models/           # SQLAlchemy database models
│   ├── repositories/     # Database access layer
│   ├── routers/          # API route handlers
│   ├── schemas/          # Pydantic validation schemas
│   ├── services/         # Business logic layer
│   └── utils/            # Helper functions
├── logs/                 # Application logs
├── scripts/              # Utility scripts (seeding, admin creation)
├── tests/                # Pytest test suite
├── .env.example          # Environment variables template
├── alembic.ini           # Alembic configuration
├── pyproject.toml        # Project metadata and tooling config
└── requirements.txt      # Python dependencies
```

## Setup & Installation

### 1. Prerequisites
- Python 3.14 (or >=3.12)
- PostgreSQL installed and running locally.

### 2. Virtual Environment
```bash
cd backend
python -m venv venv
# Windows
.\venv\Scripts\activate
# macOS/Linux
source venv/bin/activate
```

### 3. Install Dependencies
```bash
pip install -r requirements.txt
```

### 4. Environment Variables
Copy the template and configure your database connection:
```bash
cp .env.example .env
```
Ensure your `DATABASE_URL` is set correctly. The format is:
`postgresql+psycopg://<user>:<password>@<host>:<port>/<dbname>`

### 5. Database Migrations
Create the initial schema in your PostgreSQL database:
```bash
alembic revision --autogenerate -m "Initial migration"
alembic upgrade head
```

### 6. Seed Data
Populate the database with initial categories, an admin user, and sample products:
```bash
python scripts/seed.py
```

## Running the Backend

Start the FastAPI development server:
```bash
uvicorn app.main:app --reload --port 8000
```
The API will be available at `http://localhost:8000`.
- Swagger UI Docs: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`

## Connecting the Frontend

The existing Vite frontend is configured to proxy API requests in development. 
In `frontend/vite.config.ts`, ensure a proxy is set up or ensure the frontend's API client base URL points to `http://localhost:8000`. (By default, the backend CORS settings allow `http://localhost:5173` and `http://localhost:3000`).

## Testing

Run the comprehensive Pytest suite:
```bash
pytest
```
Tests use an in-memory SQLite database to run quickly and isolated from your development PostgreSQL database.

## Code Quality

Install pre-commit hooks to automatically format and lint code:
```bash
pre-commit install
```
Run manually across all files:
```bash
pre-commit run --all-files
```
