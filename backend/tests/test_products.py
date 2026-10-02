def test_get_categories(client, db):
    from app.models.product import Category
    cat1 = Category(name="Test Category 1", description="Description 1")
    cat2 = Category(name="Test Category 2", description="Description 2")
    db.add(cat1)
    db.add(cat2)
    db.commit()

    response = client.get("/api/categories")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 2
    assert data[0]["name"] == "Test Category 1"

def test_create_product_unauthorized(client):
    response = client.post(
        "/api/products",
        json={
            "name": "New Product",
            "description": "A new product",
            "price": 100.0,
            "stock": 10,
            "category_id": "test_id"
        }
    )
    assert response.status_code == 401

def test_create_product_authorized(client, db):
    # Setup seller user
    from app.models.user import User
    from app.models.product import Category
    from app.core.security import get_password_hash
    
    seller = User(
        email="seller@example.com",
        full_name="Seller User",
        hashed_password=get_password_hash("password"),
        role="seller"
    )
    db.add(seller)
    
    cat = Category(name="Tech")
    db.add(cat)
    db.commit()
    
    # Login to get token
    login_res = client.post("/api/auth/login", json={"email": "seller@example.com", "password": "password"})
    token = login_res.json()["access_token"]
    
    # Create product
    response = client.post(
        "/api/products",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "name": "New Product",
            "description": "A new product",
            "price": 100.0,
            "stock": 10,
            "category_id": cat.id
        }
    )
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "New Product"
    assert data["seller_id"] == seller.id

def test_list_products(client, db):
    from app.models.product import Product, Category
    from app.models.user import User
    
    user = User(email="test@test.com", full_name="Test", hashed_password="hashed")
    cat = Category(name="Tech")
    db.add(user)
    db.add(cat)
    db.commit()
    
    p1 = Product(name="Product A", description="Desc", price=50.0, stock=10, category_id=cat.id, seller_id=user.id)
    p2 = Product(name="Product B", description="Desc", price=150.0, stock=10, category_id=cat.id, seller_id=user.id)
    db.add(p1)
    db.add(p2)
    db.commit()
    
    response = client.get("/api/products")
    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 2
    assert len(data["items"]) == 2
