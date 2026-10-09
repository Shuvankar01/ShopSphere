"""Part 2 tests: cart coupon application, backend-computed totals, and checkout
discount application (one use per customer per coupon).

The shared `product` fixture costs 49.99 with 100 units in stock.
"""
from decimal import Decimal

PRODUCT_PRICE = Decimal("49.99")


def _auth(token):
    return {"Authorization": f"Bearer {token}"}


def _seller(client, category):
    r = client.post(
        "/api/auth/register",
        json={"full_name": "Coupon Seller", "email": "coupon.seller.p2@test.com",
              "password": "Password123!", "role": "seller"},
    )
    assert r.status_code == 200, r.text
    return {"token": r.json()["access_token"]}


def _customer(client, email="coupon.customer.p2@test.com"):
    r = client.post(
        "/api/auth/register",
        json={"full_name": "Coupon Customer", "email": email,
              "password": "Password123!", "role": "customer"},
    )
    assert r.status_code == 200, r.text
    return _auth(r.json()["access_token"])


def _product(client, category, seller):
    r = client.post(
        "/api/products",
        json={"name": "Coupon Product", "description": "coupon test product",
              "price": "25.00", "stock": 50, "category_id": category["id"]},
        headers=_auth(seller),
    )
    assert r.status_code == 201, r.text
    return r.json()["id"]


def _make_coupon(client, admin_token, **overrides):
    payload = {"code": "SAVE20", "discount_type": "percent", "discount_value": "20",
               "max_uses": 50, **overrides}
    r = client.post("/api/coupons", json=payload, headers=_auth(admin_token))
    assert r.status_code == 201, r.text
    return r.json()


class TestCartCoupon:
    def test_apply_and_remove_coupon(self, client, admin_token, customer_token, product):
        _make_coupon(client, admin_token)
        ch = _auth(customer_token)

        r = client.post("/api/cart/add", json={"product_id": product["id"], "quantity": 2}, headers=ch)
        assert r.status_code == 200
        subtotal = Decimal(str(r.json()["subtotal"]))
        assert subtotal == PRODUCT_PRICE * 2

        r = client.post("/api/cart/coupon", json={"code": "SAVE20"}, headers=ch)
        assert r.status_code == 200, r.text
        body = r.json()
        assert body["coupon_code"] == "SAVE20"
        discount = Decimal(str(body["discount_amount"]))
        assert discount > 0
        assert Decimal(str(body["total"])) == subtotal - discount

        r = client.delete("/api/cart/coupon", headers=ch)
        assert r.status_code == 200
        body = r.json()
        assert body["coupon_code"] is None
        assert Decimal(str(body["discount_amount"])) == 0
        assert Decimal(str(body["total"])) == Decimal(str(body["subtotal"]))

    def test_coupon_requires_nonempty_cart(self, client, admin_token, customer_token):
        _make_coupon(client, admin_token)
        r = client.post(
            "/api/cart/coupon", json={"code": "SAVE20"}, headers=_auth(customer_token)
        )
        assert r.status_code == 400

    def test_unknown_coupon_404(self, client, customer_token, product):
        client.post(
            "/api/cart/add", json={"product_id": product["id"], "quantity": 1},
            headers=_auth(customer_token),
        )
        r = client.post(
            "/api/cart/coupon", json={"code": "NOPE"}, headers=_auth(customer_token)
        )
        assert r.status_code == 404

    def test_inactive_coupon_rejected(self, client, admin_token, customer_token, product):
        coupon = _make_coupon(client, admin_token)
        r = client.put(f"/api/coupons/{coupon['id']}", json={"is_active": False},
                       headers=_auth(admin_token))
        assert r.status_code == 200
        client.post("/api/cart/add", json={"product_id": product["id"], "quantity": 1},
                    headers=_auth(customer_token))
        r = client.post("/api/cart/coupon", json={"code": "SAVE20"}, headers=_auth(customer_token))
        assert r.status_code == 400

    def test_min_order_amount_enforced(self, client, admin_token, category):
        _make_coupon(client, admin_token, min_order_amount="100.00")
        seller = _seller(client, category)["token"]
        pid = _product(client, category, seller=seller)
        ch = _customer(client)
        client.post("/api/cart/add", json={"product_id": pid, "quantity": 1}, headers=ch)
        r = client.post("/api/cart/coupon", json={"code": "SAVE20"}, headers=ch)
        assert r.status_code == 400
        assert "not applicable" in r.json()["detail"].lower()

    def test_fixed_value_discount_capped_at_subtotal(self, client, admin_token, category):
        _make_coupon(client, admin_token, discount_type="fixed", discount_value="500.00")
        seller = _seller(client, category)["token"]
        pid = _product(client, category, seller=seller)
        ch = _customer(client)
        client.post("/api/cart/add", json={"product_id": pid, "quantity": 1}, headers=ch)
        r = client.post("/api/cart/coupon", json={"code": "SAVE20"}, headers=ch)
        assert r.status_code == 200, r.text
        body = r.json()
        assert Decimal(str(body["discount_amount"])) == Decimal(str(body["subtotal"]))
        assert Decimal(str(body["total"])) == 0

    def test_cart_discount_updates_with_quantity(self, client, admin_token, customer_token, product):
        _make_coupon(client, admin_token)
        ch = _auth(customer_token)
        client.post("/api/cart/add", json={"product_id": product["id"], "quantity": 2}, headers=ch)
        client.post("/api/cart/coupon", json={"code": "SAVE20"}, headers=ch)
        r = client.put("/api/cart/update", json={"product_id": product["id"], "quantity": 4}, headers=ch)
        assert r.status_code == 200
        body = r.json()
        subtotal = Decimal(str(body["subtotal"]))
        discount = Decimal(str(body["discount_amount"]))
        assert discount == (subtotal * Decimal("20") / Decimal("100")).quantize(Decimal("0.01"))
        assert Decimal(str(body["total"])) == subtotal - discount


class TestCheckoutDiscount:
    def test_order_total_reflects_coupon(self, client, admin_token, customer_token, product):
        from app.core.config import settings
        from app.services import shipping

        _make_coupon(client, admin_token)
        ch = _auth(customer_token)
        client.post("/api/cart/add", json={"product_id": product["id"], "quantity": 2}, headers=ch)
        client.post("/api/cart/coupon", json={"code": "SAVE20"}, headers=ch)

        r = client.post(
            "/api/orders/create",
            json={"shipping_address": "1 Test Rd", "payment_method": "card"},
            headers=ch,
        )
        assert r.status_code == 201, r.text
        order = r.json()
        subtotal = PRODUCT_PRICE * 2
        expected_discount = (subtotal * Decimal("0.2")).quantize(Decimal("0.01"))
        taxable = subtotal - expected_discount
        expected_tax = (taxable * Decimal(str(settings.TAX_RATE))).quantize(Decimal("0.01"))
        expected_shipping = shipping.charge_for("standard")

        assert Decimal(str(order["subtotal"])) == subtotal
        assert Decimal(str(order["discount_amount"])) == expected_discount
        assert Decimal(str(order["tax_amount"])) == expected_tax
        assert Decimal(str(order["shipping_cost"])) == expected_shipping
        assert order["shipping_method"] == "standard"
        # grand total = subtotal - discount + tax + shipping (all backend-computed)
        assert Decimal(str(order["total_amount"])) == taxable + expected_tax + expected_shipping
        assert order["coupon_id"] is not None

    def test_coupon_single_use_per_user_at_checkout(self, client, admin_token, customer_token, product):
        _make_coupon(client, admin_token)
        ch = _auth(customer_token)
        # First checkout consumes the coupon.
        client.post("/api/cart/add", json={"product_id": product["id"], "quantity": 1}, headers=ch)
        client.post("/api/cart/coupon", json={"code": "SAVE20"}, headers=ch)
        r = client.post(
            "/api/orders/create",
            json={"shipping_address": "1 Test Rd", "payment_method": "card"},
            headers=ch,
        )
        assert r.status_code == 201, r.text

        # Second cart: applying the same coupon must fail (already used).
        client.post("/api/cart/add", json={"product_id": product["id"], "quantity": 1}, headers=ch)
        r = client.post("/api/cart/coupon", json={"code": "SAVE20"}, headers=ch)
        assert r.status_code == 400

    def test_order_rejects_insufficient_stock(self, client, category, seller_token):
        h = {"Authorization": f"Bearer {seller_token}"}
        r = client.post(
            "/api/products", json={"name": "One Left", "description": "single unit",
                                   "price": "10.00", "stock": 1, "category_id": category["id"]},
            headers=h,
        )
        pid = r.json()["id"]
        # Two customers both add the single unit to their carts.
        ch1 = _customer(client, email="insufficient.customer.1@test.com")
        ch2 = _customer(client, email="insufficient.customer.2@test.com")
        client.post("/api/cart/add", json={"product_id": pid, "quantity": 1}, headers=ch1)
        client.post("/api/cart/add", json={"product_id": pid, "quantity": 1}, headers=ch2)

        # The first checkout succeeds and reserves the only unit.
        r = client.post(
            "/api/orders/create",
            json={"shipping_address": "1 Test Rd", "payment_method": "card"},
            headers=ch1,
        )
        assert r.status_code == 201, r.text

        # The second checkout must fail at the atomic reserve step.
        r = client.post(
            "/api/orders/create",
            json={"shipping_address": "1 Test Rd", "payment_method": "card"},
            headers=ch2,
        )
        assert r.status_code == 400
        assert "insufficient" in r.json()["detail"].lower()

    def test_coupon_admin_crud(self, client, admin_token, seller_token):
        ah = _auth(admin_token)
        coupon = _make_coupon(client, admin_token)
        r = client.get("/api/coupons", headers=ah)
        assert r.status_code == 200
        assert any(c["id"] == coupon["id"] for c in r.json())

        # Sellers cannot manage coupons.
        r = client.get("/api/coupons", headers=_auth(seller_token))
        assert r.status_code == 403
        r = client.post("/api/coupons", json={"code": "SELLER", "discount_type": "percent",
                                              "discount_value": "10"}, headers=_auth(seller_token))
        assert r.status_code == 403
