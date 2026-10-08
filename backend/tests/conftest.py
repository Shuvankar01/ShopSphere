"""
Test configuration.

Tests run against PostgreSQL only (the `shopsphere_test` database) — the same
engine as production, so schema/constraint differences surface in tests.

    TEST_DATABASE_URL=postgresql+psycopg://shopsphere:shopsphere@localhost:5432/shopsphere_test
    (default used when the variable is unset)

SQLite is NOT allowed for tests.
"""
import os

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

# Ensure all models are imported for create_all.
# NOTE: this must come BEFORE importing the FastAPI instance, otherwise the
# `app` package shadows the `app` object from app.main.
import app.models  # noqa: F401
from app.database.session import get_db
from app.main import app
from app.models.base import Base

TEST_DATABASE_URL = os.getenv(
    "TEST_DATABASE_URL",
    "postgresql+psycopg://shopsphere:shopsphere@localhost:5432/shopsphere_test",
)

if TEST_DATABASE_URL.startswith("sqlite"):
    raise RuntimeError(
        "SQLite is not allowed for tests — set TEST_DATABASE_URL to a PostgreSQL "
        "test database (e.g. postgresql+psycopg://shopsphere:shopsphere@localhost:5432/shopsphere_test)"
    )

engine = create_engine(TEST_DATABASE_URL, pool_pre_ping=True)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


@pytest.fixture(scope="session")
def db_engine():
    # Start from a clean schema every test session (persistent test database).
    Base.metadata.drop_all(bind=engine)
    # pg_trgm powers the GIN trigram indexes declared on Product.name/description.
    with engine.connect() as conn:
        conn.execute(text("CREATE EXTENSION IF NOT EXISTS pg_trgm"))
        conn.commit()
    Base.metadata.create_all(bind=engine)
    yield engine
    Base.metadata.drop_all(bind=engine)


@pytest.fixture(scope="function")
def db(db_engine):
    connection = db_engine.connect()
    transaction = connection.begin()
    session = TestingSessionLocal(bind=connection)
    yield session
    session.close()
    transaction.rollback()
    connection.close()


@pytest.fixture(scope="function")
def client(db):
    def override_get_db():
        try:
            yield db
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


# ---------------------------------------------------------------------------
# Shared test data helpers
# ---------------------------------------------------------------------------

@pytest.fixture()
def seller_token(client):
    """Register a seller and return auth token."""
    r = client.post("/api/auth/register", json={
        "full_name": "Test Seller",
        "email": "seller@test.com",
        "password": "Password123!",
        "role": "seller",
    })
    assert r.status_code == 200, r.text
    return r.json()["access_token"]


@pytest.fixture()
def customer_token(client):
    r = client.post("/api/auth/register", json={
        "full_name": "Test Customer",
        "email": "customer@test.com",
        "password": "Password123!",
        "role": "customer",
    })
    assert r.status_code == 200, r.text
    return r.json()["access_token"]


@pytest.fixture()
def admin_token(client, db):
    """Self-registration cannot grant admin (privilege escalation is blocked),
    so register a normal user and elevate the role directly in the test DB."""
    from app.models.user import User
    r = client.post("/api/auth/register", json={
        "full_name": "Admin User",
        "email": "admin@test.com",
        "password": "Password123!",
        "role": "customer",
    })
    assert r.status_code == 200, r.text
    db.query(User).filter(User.email == "admin@test.com").update({"role": "admin"})
    db.commit()
    return r.json()["access_token"]


@pytest.fixture()
def category(client, admin_token):
    r = client.post(
        "/api/categories",
        json={"name": "Electronics", "description": "Electronic goods"},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert r.status_code == 201, r.text
    return r.json()


@pytest.fixture()
def product(client, seller_token, category):
    r = client.post(
        "/api/products",
        json={
            "name": "Test Product",
            "description": "A test product description",
            "price": "49.99",
            "stock": 100,
            "category_id": category["id"],
        },
        headers={"Authorization": f"Bearer {seller_token}"},
    )
    assert r.status_code == 201, r.text
    return r.json()
