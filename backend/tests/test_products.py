"""Tests for product catalog: CRUD, seller ownership, categories, brands, variants."""
import pytest


# ---------------------------------------------------------------------------
# Category tests
# ---------------------------------------------------------------------------

class TestCategories:
    def test_list_categories_public(self, client):
        r = client.get("/api/categories")
        assert r.status_code == 200
        assert isinstance(r.json(), list)

    def test_create_category_requires_admin(self, client, seller_token):
        r = client.post(
            "/api/categories",
            json={"name": "Clothing"},
            headers={"Authorization": f"Bearer {seller_token}"},
        )
        assert r.status_code == 403

    def test_create_category_as_admin(self, client, admin_token):
        r = client.post(
            "/api/categories",
            json={"name": "Clothing", "description": "Clothes and accessories"},
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert r.status_code == 201
        data = r.json()
        assert data["name"] == "Clothing"
        assert data["is_active"] is True

    def test_duplicate_category_rejected(self, client, admin_token, category):
        r = client.post(
            "/api/categories",
            json={"name": category["name"]},
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert r.status_code == 409

    def test_category_parent_child(self, client, admin_token):
        parent = client.post(
            "/api/categories",
            json={"name": "Computers"},
            headers={"Authorization": f"Bearer {admin_token}"},
        ).json()
        child = client.post(
            "/api/categories",
            json={"name": "Laptops", "parent_id": parent["id"]},
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert child.status_code == 201
        assert child.json()["parent_id"] == parent["id"]


# ---------------------------------------------------------------------------
# Product CRUD tests
# ---------------------------------------------------------------------------

class TestProductCRUD:
    def test_list_products_public(self, client):
        r = client.get("/api/products")
        assert r.status_code == 200
        data = r.json()
        assert "items" in data
        assert "total" in data

    def test_create_product_as_seller(self, client, seller_token, category):
        r = client.post(
            "/api/products",
            json={
                "name": "New Product",
                "description": "Product description here",
                "price": "25.00",
                "stock": 50,
                "category_id": category["id"],
            },
            headers={"Authorization": f"Bearer {seller_token}"},
        )
        assert r.status_code == 201
        data = r.json()
        assert data["name"] == "New Product"
        assert data["is_active"] is True

    def test_create_product_customer_forbidden(self, client, customer_token, category):
        r = client.post(
            "/api/products",
            json={
                "name": "Bad Product",
                "description": "Should fail",
                "price": "10.00",
                "stock": 1,
                "category_id": category["id"],
            },
            headers={"Authorization": f"Bearer {customer_token}"},
        )
        assert r.status_code == 403

    def test_get_product(self, client, product):
        r = client.get(f"/api/products/{product['id']}")
        assert r.status_code == 200
        assert r.json()["id"] == product["id"]

    def test_get_nonexistent_product(self, client):
        r = client.get("/api/products/does-not-exist")
        assert r.status_code == 404

    def test_update_product_by_owner(self, client, seller_token, product):
        r = client.put(
            f"/api/products/{product['id']}",
            json={"name": "Updated Name", "price": "59.99"},
            headers={"Authorization": f"Bearer {seller_token}"},
        )
        assert r.status_code == 200
        assert r.json()["name"] == "Updated Name"

    def test_update_product_by_other_seller(self, client, product):
        # Register a second seller
        other = client.post("/api/auth/register", json={
            "full_name": "Other Seller",
            "email": "other_seller@test.com",
            "password": "Password123!",
            "role": "seller",
        }).json()
        r = client.put(
            f"/api/products/{product['id']}",
            json={"name": "Stolen Name"},
            headers={"Authorization": f"Bearer {other['access_token']}"},
        )
        assert r.status_code == 403

    def test_delete_product_by_owner(self, client, seller_token, category):
        # Create a product to delete
        p = client.post(
            "/api/products",
            json={
                "name": "To Be Deleted",
                "description": "Temporary",
                "price": "5.00",
                "stock": 1,
                "category_id": category["id"],
            },
            headers={"Authorization": f"Bearer {seller_token}"},
        ).json()
        r = client.delete(f"/api/products/{p['id']}", headers={"Authorization": f"Bearer {seller_token}"})
        assert r.status_code == 204


# ---------------------------------------------------------------------------
# Search and filtering tests
# ---------------------------------------------------------------------------

class TestSearch:
    def test_search_by_keyword(self, client, product):
        r = client.get("/api/products", params={"q": product["name"][:5]})
        assert r.status_code == 200
        assert r.json()["total"] >= 1

    def test_filter_by_category(self, client, product):
        r = client.get("/api/products", params={"category": product["category_id"]})
        assert r.status_code == 200

    def test_filter_by_price_range(self, client, product):
        r = client.get("/api/products", params={"min": "1.00", "max": "1000.00"})
        assert r.status_code == 200

    def test_sort_by_price_asc(self, client):
        r = client.get("/api/products", params={"sort": "price_asc"})
        assert r.status_code == 200

    def test_pagination(self, client):
        r = client.get("/api/products", params={"page": 1, "limit": 5})
        assert r.status_code == 200
        data = r.json()
        assert data["page"] == 1
        assert data["limit"] == 5

    def test_search_suggestions(self, client, product):
        r = client.get("/api/products/search/suggestions", params={"q": "Te"})
        assert r.status_code == 200
        assert isinstance(r.json(), list)


# ---------------------------------------------------------------------------
# Product variants
# ---------------------------------------------------------------------------

class TestVariants:
    def test_create_variant(self, client, seller_token, product):
        r = client.post(
            f"/api/products/{product['id']}/variants",
            json={"sku": "TEST-RED-XL", "name": "Red XL", "stock": 10, "attributes": '{"color":"Red","size":"XL"}'},
            headers={"Authorization": f"Bearer {seller_token}"},
        )
        assert r.status_code == 201
        data = r.json()
        assert data["sku"] == "TEST-RED-XL"

    def test_create_variant_wrong_seller(self, client, product):
        other = client.post("/api/auth/register", json={
            "full_name": "Variant Thief",
            "email": "variantthief@test.com",
            "password": "Password123!",
            "role": "seller",
        }).json()
        r = client.post(
            f"/api/products/{product['id']}/variants",
            json={"sku": "STOLEN-SKU", "name": "Stolen"},
            headers={"Authorization": f"Bearer {other['access_token']}"},
        )
        assert r.status_code == 403


# ---------------------------------------------------------------------------
# Reviews
# ---------------------------------------------------------------------------

class TestReviews:
    def test_add_review(self, client, customer_token, product):
        r = client.post(
            f"/api/products/{product['id']}/reviews",
            json={"rating": 4, "comment": "Great product!"},
            headers={"Authorization": f"Bearer {customer_token}"},
        )
        assert r.status_code == 201
        assert r.json()["rating"] == 4

    def test_duplicate_review_rejected(self, client, customer_token, product):
        client.post(
            f"/api/products/{product['id']}/reviews",
            json={"rating": 5, "comment": "First review"},
            headers={"Authorization": f"Bearer {customer_token}"},
        )
        r = client.post(
            f"/api/products/{product['id']}/reviews",
            json={"rating": 1, "comment": "Second review"},
            headers={"Authorization": f"Bearer {customer_token}"},
        )
        assert r.status_code == 409

    def test_invalid_rating(self, client, customer_token, product):
        r = client.post(
            f"/api/products/{product['id']}/reviews",
            json={"rating": 6, "comment": "Invalid"},
            headers={"Authorization": f"Bearer {customer_token}"},
        )
        assert r.status_code == 422
