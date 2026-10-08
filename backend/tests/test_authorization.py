"""Authorization tests: seller/customer/admin scopes, IDOR protection,
payments persistence, soft-delete visibility, rating persistence."""
from decimal import Decimal

AUTH = lambda token: {"Authorization": f"Bearer {token}"}  # noqa: E731


def register(client, email, password="Password123!", role="customer", name="Auth User"):
    r = client.post("/api/auth/register", json={
        "full_name": name, "email": email, "password": password, "role": role,
    })
    assert r.status_code == 200, r.text
    return r.json()


def create_order(client, token, product, payment_method="card"):
    r = client.post(
        "/api/cart/add",
        json={"product_id": product["id"], "quantity": 1},
        headers=AUTH(token),
    )
    assert r.status_code in (200, 201), r.text
    r2 = client.post(
        "/api/orders/create",
        json={"shipping_address": "1 Test Street, Testville", "payment_method": payment_method},
        headers=AUTH(token),
    )
    assert r2.status_code == 201, r2.text
    return r2.json()


# ---------------------------------------------------------------------------
# Product visibility / soft delete / include_inactive scoping
# ---------------------------------------------------------------------------

class TestProductVisibility:
    def test_include_inactive_requires_authentication(self, client):
        r = client.get("/api/products", params={"include_inactive": "true"})
        assert r.status_code == 401

    def test_include_inactive_forbidden_for_customer(self, client, customer_token):
        r = client.get(
            "/api/products",
            params={"include_inactive": "true"},
            headers=AUTH(customer_token),
        )
        assert r.status_code == 403

    def test_seller_include_inactive_scoped_to_own_catalog(
        self, client, category, product, seller_token
    ):
        # A second seller with their own product
        other = register(client, "seller_b@test.com", role="seller", name="Seller B")
        client.post(
            "/api/products",
            json={
                "name": "B Product",
                "description": "Owned by seller B alone",
                "price": "10.00",
                "stock": 5,
                "category_id": category["id"],
            },
            headers=AUTH(other["access_token"]),
        )
        # seller A (fixture token) sees only their own products
        r = client.get(
            "/api/products",
            params={"include_inactive": "true", "limit": 100},
            headers=AUTH(seller_token),
        )
        assert r.status_code == 200
        items = r.json()["items"]
        assert items, "expected seller A to have at least one product"
        r_b = client.get(
            "/api/products",
            params={"include_inactive": "true", "limit": 100},
            headers=AUTH(other["access_token"]),
        )
        assert all(p["seller_id"] == other["user"]["id"] for p in r_b.json()["items"])
        assert all(p["seller_id"] != other["user"]["id"] for p in items)

    def test_soft_delete_hides_product_from_public(self, client, seller_token, category):
        p = client.post(
            "/api/products",
            json={
                "name": "Hidden Product",
                "description": "Will be soft deleted",
                "price": "5.00",
                "stock": 1,
                "category_id": category["id"],
            },
            headers=AUTH(seller_token),
        ).json()
        r = client.delete(f"/api/products/{p['id']}", headers=AUTH(seller_token))
        assert r.status_code == 204

        # Public: 404 on detail, absent from list
        assert client.get(f"/api/products/{p['id']}").status_code == 404
        listing = client.get("/api/products", params={"limit": 100}).json()
        assert all(item["id"] != p["id"] for item in listing["items"])

        # Owner and admin can still fetch it (is_active=False)
        r_owner = client.get(f"/api/products/{p['id']}", headers=AUTH(seller_token))
        assert r_owner.status_code == 200
        assert r_owner.json()["is_active"] is False

    def test_soft_deleted_product_hidden_from_other_logged_in_users(
        self, client, seller_token, customer_token, category
    ):
        p = client.post(
            "/api/products",
            json={
                "name": "Not Yours",
                "description": "Inactive product detail visibility",
                "price": "7.00",
                "stock": 1,
                "category_id": category["id"],
            },
            headers=AUTH(seller_token),
        ).json()
        client.delete(f"/api/products/{p['id']}", headers=AUTH(seller_token))
        assert (
            client.get(f"/api/products/{p['id']}", headers=AUTH(customer_token)).status_code
            == 404
        )


# ---------------------------------------------------------------------------
# Inventory authorization
# ---------------------------------------------------------------------------

class TestInventoryAuthorization:
    def test_customer_cannot_view_inventory(self, client, customer_token, product):
        r = client.get(
            f"/api/inventory/products/{product['id']}", headers=AUTH(customer_token)
        )
        assert r.status_code == 403

    def test_owner_seller_can_view_and_set_stock(self, client, seller_token, product):
        r = client.get(
            f"/api/inventory/products/{product['id']}", headers=AUTH(seller_token)
        )
        assert r.status_code == 200
        assert r.json()["physical_stock"] == 100  # created with product stock

        r2 = client.put(
            f"/api/inventory/products/{product['id']}",
            json={"physical_stock": 42},
            headers=AUTH(seller_token),
        )
        assert r2.status_code == 200
        assert r2.json()["physical_stock"] == 42

    def test_other_seller_cannot_manage_inventory(self, client, product):
        other = register(client, "seller_c@test.com", role="seller", name="Seller C")
        r = client.get(
            f"/api/inventory/products/{product['id']}",
            headers=AUTH(other["access_token"]),
        )
        assert r.status_code == 403

    def test_admin_can_adjust_stock(self, client, admin_token, product):
        r = client.post(
            f"/api/inventory/products/{product['id']}/adjust",
            json={"quantity": 5, "note": "restock"},
            headers=AUTH(admin_token),
        )
        assert r.status_code == 200
        assert r.json()["physical_stock"] == 105


# ---------------------------------------------------------------------------
# Order IDOR / status authorization
# ---------------------------------------------------------------------------

class TestOrderAuthorization:
    def test_owner_can_view_order(self, client, customer_token, product):
        order = create_order(client, customer_token, product)
        r = client.get(f"/api/orders/{order['id']}", headers=AUTH(customer_token))
        assert r.status_code == 200
        assert r.json()["id"] == order["id"]

    def test_other_customer_cannot_view_order_404(self, client, customer_token, product):
        order = create_order(client, customer_token, product)
        other = register(client, "nosy@example.com")
        r = client.get(
            f"/api/orders/{order['id']}", headers=AUTH(other["access_token"])
        )
        assert r.status_code == 404  # not 403: existence must not leak

    def test_seller_cannot_view_customer_order_404(self, client, customer_token, product):
        order = create_order(client, customer_token, product)
        seller = register(client, "seller_d@test.com", role="seller", name="Seller D")
        r = client.get(
            f"/api/orders/{order['id']}", headers=AUTH(seller["access_token"])
        )
        assert r.status_code == 404

    def test_admin_can_view_any_order(self, client, customer_token, admin_token, product):
        order = create_order(client, customer_token, product)
        r = client.get(f"/api/orders/{order['id']}", headers=AUTH(admin_token))
        assert r.status_code == 200

    def test_customer_cannot_update_order_status(self, client, customer_token, product):
        order = create_order(client, customer_token, product)
        r = client.put(
            f"/api/orders/{order['id']}/status",
            json={"status": "confirmed"},
            headers=AUTH(customer_token),
        )
        assert r.status_code == 403

    def test_seller_cannot_update_any_order_status(self, client, customer_token, product):
        order = create_order(client, customer_token, product)
        seller = register(client, "seller_e@test.com", role="seller", name="Seller E")
        r = client.put(
            f"/api/orders/{order['id']}/status",
            json={"status": "confirmed"},
            headers=AUTH(seller["access_token"]),
        )
        assert r.status_code == 403

    def test_admin_can_update_status_and_history_is_recorded(
        self, client, customer_token, admin_token, product, db
    ):
        from app.models.order import OrderStatusHistory
        from app.models.user import User

        order = create_order(client, customer_token, product)
        r = client.put(
            f"/api/orders/{order['id']}/status",
            json={"status": "confirmed"},
            headers=AUTH(admin_token),
        )
        assert r.status_code == 200
        assert r.json()["order_status"] == "confirmed"

        customer = db.query(User).filter(User.email == "customer@test.com").one()
        admin = db.query(User).filter(User.email == "admin@test.com").one()
        rows = (
            db.query(OrderStatusHistory)
            .filter(OrderStatusHistory.order_id == order["id"])
            .order_by(OrderStatusHistory.created_at)
            .all()
        )
        assert len(rows) == 2
        assert rows[0].from_status is None and rows[0].to_status == "pending"
        assert rows[0].changed_by == customer.id
        assert rows[1].from_status == "pending" and rows[1].to_status == "confirmed"
        assert rows[1].changed_by == admin.id

    def test_invalid_status_transition_rejected(
        self, client, customer_token, admin_token, product
    ):
        order = create_order(client, customer_token, product)
        # pending -> delivered is not a valid transition
        r2 = client.put(
            f"/api/orders/{order['id']}/status",
            json={"status": "delivered"},
            headers=AUTH(admin_token),
        )
        assert r2.status_code == 400


# ---------------------------------------------------------------------------
# Payments: ownership, state, persistence
# ---------------------------------------------------------------------------

class TestPayments:
    def test_unknown_order_returns_404(self, client, customer_token):
        r = client.post(
            "/api/payment/create",
            json={"order_id": "no-such-order", "payment_method": "card"},
            headers=AUTH(customer_token),
        )
        assert r.status_code == 404

    def test_foreign_order_returns_404(self, client, customer_token, product):
        order = create_order(client, customer_token, product)
        other = register(client, "paythief@example.com")
        r = client.post(
            "/api/payment/create",
            json={"order_id": order["id"], "payment_method": "card"},
            headers=AUTH(other["access_token"]),
        )
        assert r.status_code == 404

    def test_invalid_payment_method_rejected(self, client, customer_token, product):
        order = create_order(client, customer_token, product)
        r = client.post(
            "/api/payment/create",
            json={"order_id": order["id"], "payment_method": "bitcoin"},
            headers=AUTH(customer_token),
        )
        assert r.status_code == 422

    def test_payment_persists_and_confirms_order(
        self, client, customer_token, product, db
    ):
        from app.models.order import Order
        from app.models.payment import Payment, PaymentTransaction

        order = create_order(client, customer_token, product)
        r = client.post(
            "/api/payment/create",
            json={"order_id": order["id"], "payment_method": "paypal"},
            headers=AUTH(customer_token),
        )
        assert r.status_code == 200, r.text
        body = r.json()
        assert body["status"] == "succeeded"
        assert body["transaction_id"].startswith("txn_")

        # Order state transitioned server-side
        r2 = client.get(f"/api/orders/{order['id']}", headers=AUTH(customer_token))
        assert r2.json()["payment_status"] == "paid"
        assert r2.json()["order_status"] == "confirmed"

        # Rows persisted
        payment = db.query(Payment).filter(Payment.order_id == order["id"]).one()
        assert str(payment.amount) == str(
            db.query(Order).filter(Order.id == order["id"]).one().total_amount
        )
        assert payment.status == "succeeded"
        txn = (
            db.query(PaymentTransaction)
            .filter(PaymentTransaction.payment_id == payment.id)
            .one()
        )
        assert txn.reference == body["transaction_id"]
        assert txn.type == "charge"

    def test_double_payment_conflict(self, client, customer_token, product):
        order = create_order(client, customer_token, product)
        first = client.post(
            "/api/payment/create",
            json={"order_id": order["id"], "payment_method": "card"},
            headers=AUTH(customer_token),
        )
        assert first.status_code == 200
        second = client.post(
            "/api/payment/create",
            json={"order_id": order["id"], "payment_method": "card"},
            headers=AUTH(customer_token),
        )
        assert second.status_code == 409

    def test_paypal_checkout_supported(self, client, customer_token, product):
        # The checkout UI offers card/paypal/cod — paypal must not 422.
        order = create_order(client, customer_token, product, payment_method="paypal")
        assert order["payment_method"] == "paypal"


# ---------------------------------------------------------------------------
# Admin-only endpoints
# ---------------------------------------------------------------------------

class TestAdminOnly:
    def test_customer_blocked_from_admin_dashboard(self, client, customer_token):
        assert (
            client.get("/api/admin/dashboard", headers=AUTH(customer_token)).status_code
            == 403
        )

    def test_seller_blocked_from_admin_users(self, client):
        seller = register(client, "seller_f@test.com", role="seller", name="Seller F")
        assert (
            client.get("/api/admin/users", headers=AUTH(seller["access_token"])).status_code
            == 403
        )

    def test_admin_dashboard_returns_decimal_revenue(self, client, admin_token):
        r = client.get("/api/admin/dashboard", headers=AUTH(admin_token))
        assert r.status_code == 200
        body = r.json()
        # Pydantic v2 serializes Decimal as a JSON string — must parse, not be float.
        from decimal import Decimal

        assert Decimal(str(body["revenue"])) >= Decimal("0")
        assert body["total_users"] >= 1


# ---------------------------------------------------------------------------
# Rating persistence
# ---------------------------------------------------------------------------

class TestRatingPersistence:
    def test_review_updates_product_rating_in_response_and_db(
        self, client, product, customer_token, db
    ):
        from app.models.product import Product

        r = client.post(
            f"/api/products/{product['id']}/reviews",
            json={"rating": 4, "comment": "Solid product, would buy again"},
            headers=AUTH(customer_token),
        )
        assert r.status_code == 201, r.text

        got = client.get(f"/api/products/{product['id']}").json()
        assert got["rating"] is not None
        assert Decimal(got["rating"]) == Decimal("4")
        assert got["review_count"] == 1

        row = db.query(Product).filter(Product.id == product["id"]).one()
        assert row.rating == 4
        assert row.review_count == 1
