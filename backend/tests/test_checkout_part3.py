"""Part 3 tests: backend-authoritative checkout totals, atomic order creation,
the controlled order lifecycle, DEMO two-phase payments + idempotent webhook,
coupons (restrictions / limits / concurrency), refunds, returns, addresses, and
review verification.

Money is always computed by the backend; the client only ever supplies an
address, a shipping method and an (optional) coupon — never an amount.
"""
from __future__ import annotations

import threading
import uuid
from decimal import Decimal

from sqlalchemy.orm import sessionmaker

from app.core.config import settings
from app.services import shipping

AUTH = lambda token: {"Authorization": f"Bearer {token}"}  # noqa: E731


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def register(client, email, role="customer", name="P3 User", password="Password123!"):
    r = client.post(
        "/api/auth/register",
        json={"full_name": name, "email": email, "password": password, "role": role},
    )
    assert r.status_code == 200, r.text
    return r.json()["access_token"]


def make_product(client, token, category, name=None, price="49.99", stock=100):
    r = client.post(
        "/api/products",
        json={
            "name": name or f"P3 Product {uuid.uuid4().hex[:6]}",
            "description": "part three product",
            "price": price,
            "stock": stock,
            "category_id": category["id"],
        },
        headers=AUTH(token),
    )
    assert r.status_code == 201, r.text
    return r.json()


def add_to_cart(client, token, product_id, qty=1):
    r = client.post(
        "/api/cart/add",
        json={"product_id": product_id, "quantity": qty},
        headers=AUTH(token),
    )
    assert r.status_code in (200, 201), r.text
    return r


def checkout(client, token, **overrides):
    payload = {
        "shipping_address": "1 Test Street, Testville",
        "payment_method": "card",
    }
    payload.update(overrides)
    # An address id is mutually exclusive with the free-text address.
    if payload.get("shipping_address_id"):
        payload.pop("shipping_address", None)
    return client.post("/api/orders/create", json=payload, headers=AUTH(token))


def pay_success(client, token, order_id):
    r = client.post(
        "/api/payment/create",
        json={"order_id": order_id, "payment_method": "card"},
        headers=AUTH(token),
    )
    assert r.status_code == 200, r.text
    txn = r.json()["transaction_id"]
    done = client.post(
        f"/api/payment/{txn}/complete",
        json={"result": "success"},
        headers=AUTH(token),
    )
    assert done.status_code == 200, done.text
    return txn


def buy(client, token, product, qty=1, **checkout_kwargs):
    """Cart → order → demo payment success. Returns the created order dict."""
    add_to_cart(client, token, product["id"], qty)
    r = checkout(client, token, **checkout_kwargs)
    assert r.status_code == 201, r.text
    order = r.json()
    pay_success(client, token, order["id"])
    return order


def advance_order(client, admin_token, order_id, status, body=None):
    r = client.put(
        f"/api/orders/{order_id}/status",
        json={"status": status, **(body or {})},
        headers=AUTH(admin_token),
    )
    return r


def advance_to_delivered(client, admin_token, order_id):
    for status in ("processing", "packed", "shipped", "out_for_delivery", "delivered"):
        r = advance_order(client, admin_token, order_id, status)
        assert r.status_code == 200, r.text


def available_stock(client, seller_token, product_id):
    """Reservations live on the Inventory row, not the catalog Product.stock."""
    r = client.get(f"/api/inventory/products/{product_id}", headers=AUTH(seller_token))
    assert r.status_code == 200, r.text
    return r.json()["available_stock"]


# ---------------------------------------------------------------------------
# 1. Backend-authoritative totals
# ---------------------------------------------------------------------------

class TestCheckoutTotals:
    def test_backend_computes_totals_and_ignores_client_amounts(
        self, client, seller_token, customer_token, category
    ):
        product = make_product(client, seller_token, category, price="49.99")
        add_to_cart(client, customer_token, product["id"], qty=2)

        # The client tries to dictate the money — it must be ignored outright.
        r = client.post(
            "/api/orders/create",
            json={
                "shipping_address": "1 Test St",
                "payment_method": "card",
                "shipping_method": "express",
                "subtotal": "1.00",
                "tax_amount": "0.00",
                "shipping_cost": "0.00",
                "total_amount": "1.00",
            },
            headers=AUTH(customer_token),
        )
        assert r.status_code == 201, r.text
        order = r.json()

        subtotal = Decimal("49.99") * 2
        expected_tax = (subtotal * Decimal(str(settings.TAX_RATE))).quantize(Decimal("0.01"))
        expected_shipping = shipping.charge_for("express")
        assert Decimal(order["subtotal"]) == subtotal
        assert Decimal(order["discount_amount"]) == Decimal("0.00")
        assert Decimal(order["tax_amount"]) == expected_tax
        assert Decimal(order["shipping_cost"]) == expected_shipping
        assert Decimal(order["total_amount"]) == subtotal + expected_tax + expected_shipping

    def test_default_shipping_method_is_standard(
        self, client, seller_token, customer_token, category
    ):
        product = make_product(client, seller_token, category, price="10.00")
        r = buy(client, customer_token, product)
        assert r["shipping_method"] == "standard"
        assert Decimal(r["shipping_cost"]) == shipping.charge_for("standard")

    def test_empty_cart_cannot_checkout(self, client, customer_token):
        r = checkout(client, customer_token)
        assert r.status_code == 400

    def test_checkout_quote_matches_created_order(
        self, client, seller_token, customer_token, admin_token, category
    ):
        product = make_product(client, seller_token, category, price="49.99")
        make_coupon(client, admin_token, "P3QUOTE", discount_value="10")
        add_to_cart(client, customer_token, product["id"], qty=2)
        client.post(
            "/api/cart/coupon", json={"code": "P3QUOTE"}, headers=AUTH(customer_token)
        )

        quote = client.post(
            "/api/orders/quote",
            json={"shipping_method": "priority"},
            headers=AUTH(customer_token),
        )
        assert quote.status_code == 200, quote.text
        q = quote.json()
        assert q["coupon_code"] == "P3QUOTE"
        assert q["shipping_method"] == "priority"
        assert q["currency"] == "INR"

        order = checkout(client, customer_token, shipping_method="priority").json()
        for field in ("subtotal", "discount_amount", "tax_amount", "shipping_cost", "total_amount"):
            assert Decimal(str(q[field])) == Decimal(str(order[field])), field

    def test_order_starts_pending_and_unpaid(
        self, client, seller_token, customer_token, category
    ):
        product = make_product(client, seller_token, category)
        add_to_cart(client, customer_token, product["id"])
        order = checkout(client, customer_token).json()
        assert order["order_status"] == "pending"
        assert order["payment_status"] == "pending"


# ---------------------------------------------------------------------------
# 2. Atomic order creation + inventory reservation
# ---------------------------------------------------------------------------

class TestOrderAtomicity:
    def test_checkout_reserves_stock_clears_cart_and_records_items(
        self, client, seller_token, customer_token, category
    ):
        product = make_product(client, seller_token, category, stock=5)
        add_to_cart(client, customer_token, product["id"], qty=2)
        order = checkout(client, customer_token).json()
        assert len(order["items"]) == 1
        assert order["items"][0]["quantity"] == 2

        # Cart cleared.
        cart = client.get("/api/cart", headers=AUTH(customer_token)).json()
        assert cart["items"] == []

        # Stock reserved (available quantity drops).
        assert available_stock(client, seller_token, product["id"]) == 3

    def test_failed_checkout_leaves_no_order_row(
        self, client, seller_token, customer_token, category
    ):
        # Empty cart → checkout fails before any order is created.
        r = checkout(client, customer_token)
        assert r.status_code == 400
        orders = client.get("/api/orders", headers=AUTH(customer_token)).json()
        assert orders == []

    def test_second_buyer_of_last_unit_rejected(
        self, client, seller_token, category
    ):
        product = make_product(client, seller_token, category, price="10.00", stock=1)
        buyer1 = register(client, f"atom1.{uuid.uuid4().hex[:6]}@test.com")
        buyer2 = register(client, f"atom2.{uuid.uuid4().hex[:6]}@test.com")
        add_to_cart(client, buyer1, product["id"], qty=1)
        add_to_cart(client, buyer2, product["id"], qty=1)

        first = checkout(client, buyer1)
        assert first.status_code == 201, first.text

        second = checkout(client, buyer2)
        assert second.status_code == 400, second.text
        assert "insufficient" in second.json()["detail"].lower()


# ---------------------------------------------------------------------------
# 3. Order lifecycle
# ---------------------------------------------------------------------------

class TestOrderLifecycle:
    def test_admin_full_lifecycle_generates_tracking_and_shipment_status(
        self, client, seller_token, customer_token, admin_token, category
    ):
        product = make_product(client, seller_token, category)
        order = buy(client, customer_token, product)
        current = client.get(f"/api/orders/{order['id']}", headers=AUTH(customer_token)).json()
        assert current["order_status"] == "confirmed"

        assert advance_order(client, admin_token, order["id"], "processing").status_code == 200
        assert advance_order(client, admin_token, order["id"], "packed").status_code == 200
        shipped = advance_order(client, admin_token, order["id"], "shipped")
        assert shipped.status_code == 200, shipped.text
        body = shipped.json()
        assert body["tracking_number"].startswith("DEMO")
        assert body["shipment_status"] == "shipped"

        assert advance_order(
            client, admin_token, order["id"], "out_for_delivery"
        ).status_code == 200
        assert advance_order(client, admin_token, order["id"], "delivered").status_code == 200
        final = client.get(f"/api/orders/{order['id']}", headers=AUTH(customer_token)).json()
        assert final["order_status"] == "delivered"
        assert final["shipment_status"] == "delivered"

        # Every move is recorded on the timeline.
        statuses = [h["to_status"] for h in final["status_history"]]
        assert statuses == [
            "pending", "confirmed", "processing", "packed",
            "shipped", "out_for_delivery", "delivered",
        ]

    def test_invalid_transition_rejected(
        self, client, seller_token, customer_token, admin_token, category
    ):
        product = make_product(client, seller_token, category)
        order = buy(client, customer_token, product)
        r = advance_order(client, admin_token, order["id"], "delivered")
        assert r.status_code == 400

    def test_seller_cannot_update_order_status(
        self, client, seller_token, customer_token, category
    ):
        product = make_product(client, seller_token, category)
        order = buy(client, customer_token, product)
        r = advance_order(client, seller_token, order["id"], "processing")
        assert r.status_code == 403

    def test_customer_cancel_releases_stock_and_refunds(
        self, client, seller_token, customer_token, admin_token, category
    ):
        product = make_product(client, seller_token, category, stock=4)
        add_to_cart(client, customer_token, product["id"], qty=2)
        order = checkout(client, customer_token).json()
        pay_success(client, customer_token, order["id"])
        assert available_stock(client, seller_token, product["id"]) == 2

        r = client.post(
            f"/api/orders/{order['id']}/cancel",
            headers=AUTH(customer_token),
        )
        assert r.status_code == 200, r.text
        body = r.json()
        assert body["order_status"] == "cancelled"
        assert body["payment_status"] == "refunded"
        assert body["shipment_status"] == "cancelled"
        # Stock returned.
        assert available_stock(client, seller_token, product["id"]) == 4
        # A refund row exists.
        refunds = client.get(
            f"/api/refunds?order_id={order['id']}", headers=AUTH(admin_token)
        ).json()
        assert len(refunds) == 1
        assert refunds[0]["status"] == "completed"

    def test_cannot_cancel_after_shipping(
        self, client, seller_token, customer_token, admin_token, category
    ):
        product = make_product(client, seller_token, category)
        order = buy(client, customer_token, product)
        advance_order(client, admin_token, order["id"], "processing")
        advance_order(client, admin_token, order["id"], "packed")
        advance_order(client, admin_token, order["id"], "shipped")

        r = client.post(
            f"/api/orders/{order['id']}/cancel", headers=AUTH(customer_token)
        )
        assert r.status_code == 400


# ---------------------------------------------------------------------------
# 4. DEMO two-phase payments + webhook
# ---------------------------------------------------------------------------

class TestDemoPayments:
    def test_success_marks_paid_and_confirms(
        self, client, seller_token, customer_token, category
    ):
        product = make_product(client, seller_token, category)
        add_to_cart(client, customer_token, product["id"])
        order = checkout(client, customer_token).json()

        created = client.post(
            "/api/payment/create",
            json={"order_id": order["id"], "payment_method": "card"},
            headers=AUTH(customer_token),
        ).json()
        assert created["status"] == "pending"
        assert created["provider"] == "DEMO"
        assert created["transaction_id"].startswith("demo_")

        done = client.post(
            f"/api/payment/{created['transaction_id']}/complete",
            json={"result": "success"},
            headers=AUTH(customer_token),
        )
        assert done.status_code == 200
        assert done.json()["status"] == "succeeded"

        got = client.get(f"/api/orders/{order['id']}", headers=AUTH(customer_token)).json()
        assert got["payment_status"] == "paid"
        assert got["order_status"] == "confirmed"

    def test_failure_and_cancel_leave_order_unpaid_but_retryable(
        self, client, seller_token, customer_token, category
    ):
        product = make_product(client, seller_token, category)
        add_to_cart(client, customer_token, product["id"])
        order = checkout(client, customer_token).json()

        for result in ("failure", "cancel"):
            created = client.post(
                "/api/payment/create",
                json={"order_id": order["id"], "payment_method": "card"},
                headers=AUTH(customer_token),
            ).json()
            done = client.post(
                f"/api/payment/{created['transaction_id']}/complete",
                json={"result": result},
                headers=AUTH(customer_token),
            )
            assert done.status_code == 200, done.text
            got = client.get(
                f"/api/orders/{order['id']}", headers=AUTH(customer_token)
            ).json()
            assert got["payment_status"] == "pending"
            assert got["order_status"] == "pending"

        # A fresh attempt after failures/cancel succeeds.
        txn = pay_success(client, customer_token, order["id"])
        got = client.get(f"/api/orders/{order['id']}", headers=AUTH(customer_token)).json()
        assert got["payment_status"] == "paid"
        assert txn.startswith("demo_")

    def test_foreign_user_cannot_touch_payment(
        self, client, seller_token, customer_token, category
    ):
        product = make_product(client, seller_token, category)
        add_to_cart(client, customer_token, product["id"])
        order = checkout(client, customer_token).json()
        created = client.post(
            "/api/payment/create",
            json={"order_id": order["id"], "payment_method": "card"},
            headers=AUTH(customer_token),
        ).json()

        other = register(client, f"intruder.{uuid.uuid4().hex[:6]}@test.com")
        r = client.post(
            f"/api/payment/{created['transaction_id']}/complete",
            json={"result": "success"},
            headers=AUTH(other),
        )
        assert r.status_code == 404

    def test_client_cannot_mark_paid_by_calling_status_endpoint(
        self, client, seller_token, customer_token, category
    ):
        product = make_product(client, seller_token, category)
        add_to_cart(client, customer_token, product["id"])
        order = checkout(client, customer_token).json()
        # Customers can only cancel; they cannot drive fulfillment/payment state.
        r = advance_order(client, customer_token, order["id"], "delivered")
        assert r.status_code == 403
        got = client.get(f"/api/orders/{order['id']}", headers=AUTH(customer_token)).json()
        assert got["payment_status"] == "pending"

    def test_webhook_success_and_duplicate_is_idempotent(
        self, client, seller_token, customer_token, category
    ):
        product = make_product(client, seller_token, category)
        add_to_cart(client, customer_token, product["id"])
        order = checkout(client, customer_token).json()
        created = client.post(
            "/api/payment/create",
            json={"order_id": order["id"], "payment_method": "card"},
            headers=AUTH(customer_token),
        ).json()

        event = {"event": "payment.succeeded", "transaction_id": created["transaction_id"]}
        first = client.post("/api/payment/webhook", json=event)
        assert first.status_code == 200, first.text
        assert first.json()["idempotent"] is False

        # Re-delivery of the same event is acknowledged, not reprocessed.
        second = client.post("/api/payment/webhook", json=event)
        assert second.status_code == 200
        assert second.json()["idempotent"] is True

        got = client.get(f"/api/orders/{order['id']}", headers=AUTH(customer_token)).json()
        assert got["payment_status"] == "paid"

    def test_webhook_rejects_impossible_transition(
        self, client, seller_token, customer_token, category
    ):
        product = make_product(client, seller_token, category)
        add_to_cart(client, customer_token, product["id"])
        order = checkout(client, customer_token).json()
        created = client.post(
            "/api/payment/create",
            json={"order_id": order["id"], "payment_method": "card"},
            headers=AUTH(customer_token),
        ).json()
        # Fail the charge first...
        client.post(
            f"/api/payment/{created['transaction_id']}/complete",
            json={"result": "failure"},
            headers=AUTH(customer_token),
        )
        # ...then try to settle it as succeeded via webhook → conflict.
        r = client.post(
            "/api/payment/webhook",
            json={"event": "payment.succeeded", "transaction_id": created["transaction_id"]},
        )
        assert r.status_code == 409

    def test_webhook_amount_mismatch_rejected(
        self, client, seller_token, customer_token, category
    ):
        product = make_product(client, seller_token, category)
        add_to_cart(client, customer_token, product["id"])
        order = checkout(client, customer_token).json()
        created = client.post(
            "/api/payment/create",
            json={"order_id": order["id"], "payment_method": "card"},
            headers=AUTH(customer_token),
        ).json()
        r = client.post(
            "/api/payment/webhook",
            json={
                "event": "payment.succeeded",
                "transaction_id": created["transaction_id"],
                "amount": "1.00",
            },
        )
        assert r.status_code == 400

    def test_double_payment_conflict_on_pending(
        self, client, seller_token, customer_token, category
    ):
        product = make_product(client, seller_token, category)
        add_to_cart(client, customer_token, product["id"])
        order = checkout(client, customer_token).json()
        first = client.post(
            "/api/payment/create",
            json={"order_id": order["id"], "payment_method": "card"},
            headers=AUTH(customer_token),
        ).json()
        second = client.post(
            "/api/payment/create",
            json={"order_id": order["id"], "payment_method": "card"},
            headers=AUTH(customer_token),
        )
        assert second.status_code == 409
        assert first["status"] == "pending"


# ---------------------------------------------------------------------------
# 5. Coupons (restrictions, limits, race-safety)
# ---------------------------------------------------------------------------

def make_coupon(client, admin_token, code, **overrides):
    payload = {"code": code, "discount_type": "percent", "discount_value": "10"}
    payload.update(overrides)
    r = client.post("/api/coupons", json=payload, headers=AUTH(admin_token))
    assert r.status_code == 201, r.text
    return r.json()


class TestCoupons:
    def test_percent_coupon_and_rounding_on_checkout(
        self, client, seller_token, customer_token, admin_token, category
    ):
        product = make_product(client, seller_token, category, price="50.00")
        make_coupon(client, admin_token, "P3PCT", discount_value="20")
        add_to_cart(client, customer_token, product["id"], qty=2)
        apply = client.post("/api/cart/coupon", json={"code": "P3PCT"}, headers=AUTH(customer_token))
        assert apply.status_code == 200, apply.text

        order = checkout(client, customer_token).json()
        subtotal = Decimal("100.00")
        discount = Decimal("20.00")
        taxable = subtotal - discount
        tax = (taxable * Decimal(str(settings.TAX_RATE))).quantize(Decimal("0.01"))
        assert Decimal(order["discount_amount"]) == discount
        assert Decimal(order["tax_amount"]) == tax
        assert Decimal(order["total_amount"]) == taxable + tax + shipping.charge_for("standard")

    def test_max_discount_cap_applied(
        self, client, seller_token, customer_token, admin_token, category
    ):
        product = make_product(client, seller_token, category, price="100.00")
        make_coupon(
            client, admin_token, "P3CAP", discount_value="50", max_discount_amount="20"
        )
        add_to_cart(client, customer_token, product["id"], qty=1)
        client.post("/api/cart/coupon", json={"code": "P3CAP"}, headers=AUTH(customer_token))
        order = checkout(client, customer_token).json()
        # 50% of 100 = 50, capped at 20.
        assert Decimal(order["discount_amount"]) == Decimal("20.00")

    def test_min_order_amount_gate(
        self, client, seller_token, customer_token, admin_token, category
    ):
        product = make_product(client, seller_token, category, price="30.00")
        make_coupon(client, admin_token, "P3MIN", min_order_amount="100")
        add_to_cart(client, customer_token, product["id"], qty=1)
        r = client.post("/api/cart/coupon", json={"code": "P3MIN"}, headers=AUTH(customer_token))
        assert r.status_code == 400

    def test_per_user_limit_reached_on_second_checkout(
        self, client, seller_token, customer_token, admin_token, category
    ):
        product = make_product(client, seller_token, category, price="20.00", stock=10)
        make_coupon(client, admin_token, "P3USER", discount_value="10", per_user_limit=1)

        add_to_cart(client, customer_token, product["id"], qty=1)
        client.post("/api/cart/coupon", json={"code": "P3USER"}, headers=AUTH(customer_token))
        assert checkout(client, customer_token).status_code == 201

        # Second use rejected at apply time.
        add_to_cart(client, customer_token, product["id"], qty=1)
        r = client.post("/api/cart/coupon", json={"code": "P3USER"}, headers=AUTH(customer_token))
        assert r.status_code == 400

    def test_global_max_uses_blocks_second_buyer(
        self, client, seller_token, admin_token, category
    ):
        product = make_product(client, seller_token, category, price="20.00", stock=10)
        make_coupon(
            client, admin_token, "P3GLOBAL", discount_value="10",
            max_uses=1, per_user_limit=5,
        )
        b1 = register(client, f"g1.{uuid.uuid4().hex[:6]}@test.com")
        b2 = register(client, f"g2.{uuid.uuid4().hex[:6]}@test.com")

        add_to_cart(client, b1, product["id"], qty=1)
        client.post("/api/cart/coupon", json={"code": "P3GLOBAL"}, headers=AUTH(b1))
        assert checkout(client, b1).status_code == 201

        # Second buyer can no longer apply the exhausted coupon.
        add_to_cart(client, b2, product["id"], qty=1)
        r = client.post("/api/cart/coupon", json={"code": "P3GLOBAL"}, headers=AUTH(b2))
        assert r.status_code == 400

    def test_product_restriction_limits_discount_base(
        self, client, seller_token, customer_token, admin_token, category
    ):
        p_a = make_product(client, seller_token, category, price="20.00")
        p_b = make_product(client, seller_token, category, price="80.00")
        make_coupon(
            client, admin_token, "P3RESTR",
            discount_type="fixed", discount_value="5",
            applies_to_product_ids=[p_a["id"]],
        )
        add_to_cart(client, customer_token, p_a["id"], qty=1)
        add_to_cart(client, customer_token, p_b["id"], qty=1)
        client.post("/api/cart/coupon", json={"code": "P3RESTR"}, headers=AUTH(customer_token))
        order = checkout(client, customer_token).json()
        # Fixed ₹5 off the eligible ₹20 line — not the ₹100 cart.
        assert Decimal(order["discount_amount"]) == Decimal("5.00")

    def test_restriction_without_qualifying_line_rejected(
        self, client, seller_token, customer_token, admin_token, category
    ):
        p_a = make_product(client, seller_token, category, price="20.00")
        p_b = make_product(client, seller_token, category, price="80.00")
        make_coupon(
            client, admin_token, "P3RESTR2",
            discount_type="fixed", discount_value="5",
            applies_to_product_ids=[p_a["id"]],
        )
        add_to_cart(client, customer_token, p_b["id"], qty=1)
        r = client.post(
            "/api/cart/coupon", json={"code": "P3RESTR2"}, headers=AUTH(customer_token)
        )
        assert r.status_code == 400

    def test_inactive_coupon_rejected(
        self, client, seller_token, customer_token, admin_token, category
    ):
        product = make_product(client, seller_token, category, price="20.00")
        make_coupon(client, admin_token, "P3OFF", is_active=False)
        add_to_cart(client, customer_token, product["id"], qty=1)
        r = client.post("/api/cart/coupon", json={"code": "P3OFF"}, headers=AUTH(customer_token))
        assert r.status_code == 400

    def test_seller_cannot_manage_coupons(self, client, seller_token):
        r = client.post(
            "/api/coupons",
            json={"code": "NOPE", "discount_type": "percent", "discount_value": "10"},
            headers=AUTH(seller_token),
        )
        assert r.status_code == 403


def test_coupon_race_exactly_one_winner(db_engine):
    """Two independent sessions/threads race for the last use of a coupon.
    Row locking must let exactly one through — this cannot be exercised via the
    shared client fixture session (which serialises everything)."""
    from app.core.exceptions import BadRequestException
    from app.models.coupon import Coupon, CouponUsage
    from app.models.user import User
    from app.repositories.coupon_repo import CouponRepository

    SessionLocal = sessionmaker(bind=db_engine, autoflush=False, autocommit=False)

    user_id = str(uuid.uuid4())
    coupon_id = str(uuid.uuid4())
    code = f"RACE{uuid.uuid4().hex[:8].upper()}"

    setup = SessionLocal()
    setup.add(
        User(
            id=user_id,
            full_name="Race User",
            email=f"race.{uuid.uuid4().hex}@test.com",
            hashed_password="x",
            role="customer",
        )
    )
    setup.add(
        Coupon(
            id=coupon_id,
            code=code,
            discount_type="percent",
            discount_value=Decimal("10"),
            max_uses=1,
            per_user_limit=5,
            used_count=0,
            is_active=True,
        )
    )
    setup.commit()
    setup.close()

    results: list[str] = []
    barrier = threading.Barrier(2)

    def worker():
        session = SessionLocal()
        try:
            barrier.wait()
            repo = CouponRepository(session)
            coupon = repo.get(coupon_id)
            repo.record_usage(
                coupon, user_id, Decimal("5.00"), subtotal=Decimal("50.00"), items=[]
            )
            session.commit()
            results.append("ok")
        except BadRequestException:
            session.rollback()
            results.append("rejected")
        except Exception as exc:  # pragma: no cover - diagnostic
            session.rollback()
            results.append(f"error:{type(exc).__name__}")
        finally:
            session.close()

    threads = [threading.Thread(target=worker) for _ in range(2)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    assert results.count("ok") == 1, results
    assert results.count("rejected") == 1, results

    check = SessionLocal()
    try:
        coupon = check.query(Coupon).filter(Coupon.id == coupon_id).one()
        assert coupon.used_count == 1
        usages = check.query(CouponUsage).filter(CouponUsage.coupon_id == coupon_id).count()
        assert usages == 1

        # Cleanup committed rows so other tests see an unchanged database.
        check.query(CouponUsage).filter(CouponUsage.coupon_id == coupon_id).delete()
        check.query(Coupon).filter(Coupon.id == coupon_id).delete()
        check.query(User).filter(User.id == user_id).delete()
        check.commit()
    finally:
        check.close()


# ---------------------------------------------------------------------------
# 6. Refunds
# ---------------------------------------------------------------------------

class TestRefunds:
    def test_full_refund_updates_order_and_payment(
        self, client, seller_token, customer_token, admin_token, category
    ):
        product = make_product(client, seller_token, category, price="40.00")
        order = buy(client, customer_token, product)
        total = Decimal(order["total_amount"])

        r = client.post(
            "/api/refunds",
            json={
                "order_id": order["id"],
                "amount": str(total),
                "reason": "customer request",
                "idempotency_key": f"k-{uuid.uuid4().hex}",
            },
            headers=AUTH(admin_token),
        )
        assert r.status_code == 201, r.text
        refund = r.json()
        assert refund["status"] == "completed"
        assert refund["provider_reference"]

        got = client.get(f"/api/orders/{order['id']}", headers=AUTH(customer_token)).json()
        assert got["payment_status"] == "refunded"

    def test_partial_refund_marks_partially_refunded(
        self, client, seller_token, customer_token, admin_token, category
    ):
        product = make_product(client, seller_token, category, price="40.00")
        order = buy(client, customer_token, product)
        half = (Decimal(order["total_amount"]) / 2).quantize(Decimal("0.01"))

        r = client.post(
            "/api/refunds",
            json={"order_id": order["id"], "amount": str(half)},
            headers=AUTH(admin_token),
        )
        assert r.status_code == 201, r.text
        got = client.get(f"/api/orders/{order['id']}", headers=AUTH(customer_token)).json()
        assert got["payment_status"] == "partially_refunded"

    def test_refund_cannot_exceed_captured_amount(
        self, client, seller_token, customer_token, admin_token, category
    ):
        product = make_product(client, seller_token, category, price="40.00")
        order = buy(client, customer_token, product)
        too_much = Decimal(order["total_amount"]) + Decimal("100.00")
        r = client.post(
            "/api/refunds",
            json={"order_id": order["id"], "amount": str(too_much)},
            headers=AUTH(admin_token),
        )
        assert r.status_code == 400

    def test_refund_is_idempotent_by_key(
        self, client, seller_token, customer_token, admin_token, category
    ):
        product = make_product(client, seller_token, category, price="40.00")
        order = buy(client, customer_token, product)
        key = f"idem-{uuid.uuid4().hex}"
        payload = {"order_id": order["id"], "amount": "5.00", "idempotency_key": key}

        first = client.post("/api/refunds", json=payload, headers=AUTH(admin_token)).json()
        second = client.post("/api/refunds", json=payload, headers=AUTH(admin_token)).json()
        assert first["id"] == second["id"]

    def test_refund_requires_captured_payment(
        self, client, seller_token, customer_token, admin_token, category
    ):
        product = make_product(client, seller_token, category, price="40.00")
        add_to_cart(client, customer_token, product["id"])
        order = checkout(client, customer_token).json()  # unpaid
        r = client.post(
            "/api/refunds",
            json={"order_id": order["id"], "amount": "5.00"},
            headers=AUTH(admin_token),
        )
        assert r.status_code == 400

    def test_non_admin_cannot_refund(
        self, client, seller_token, customer_token, category
    ):
        product = make_product(client, seller_token, category, price="40.00")
        order = buy(client, customer_token, product)
        r = client.post(
            "/api/refunds",
            json={"order_id": order["id"], "amount": "5.00"},
            headers=AUTH(customer_token),
        )
        assert r.status_code == 403


# ---------------------------------------------------------------------------
# 7. Returns (separate from payment state)
# ---------------------------------------------------------------------------

class TestReturns:
    def _delivered_order(self, client, seller_token, customer_token, admin_token, category):
        product = make_product(client, seller_token, category, price="30.00")
        order = buy(client, customer_token, product)
        advance_to_delivered(client, admin_token, order["id"])
        return order

    def test_return_only_for_delivered_orders(
        self, client, seller_token, customer_token, category
    ):
        product = make_product(client, seller_token, category, price="30.00")
        order = buy(client, customer_token, product)  # confirmed, not delivered
        r = client.post(
            "/api/returns",
            json={
                "order_id": order["id"],
                "reason": "changed my mind",
                "items": [{"order_item_id": order["items"][0]["id"], "quantity": 1}],
            },
            headers=AUTH(customer_token),
        )
        assert r.status_code == 400

    def test_full_return_flow_with_refund(
        self, client, seller_token, customer_token, admin_token, category
    ):
        order = self._delivered_order(
            client, seller_token, customer_token, admin_token, category
        )
        item_id = order["items"][0]["id"]

        created = client.post(
            "/api/returns",
            json={
                "order_id": order["id"],
                "reason": "defective on arrival",
                "items": [{"order_item_id": item_id, "quantity": 1}],
            },
            headers=AUTH(customer_token),
        )
        assert created.status_code == 201, created.text
        ret = created.json()
        assert ret["status"] == "requested"

        # Cannot jump straight to completed.
        bad = client.post(
            f"/api/admin/returns/{ret['id']}/complete", headers=AUTH(admin_token)
        )
        assert bad.status_code == 400

        assert client.post(
            f"/api/admin/returns/{ret['id']}/approve", headers=AUTH(admin_token)
        ).json()["status"] == "approved"
        assert client.post(
            f"/api/admin/returns/{ret['id']}/receive", headers=AUTH(admin_token)
        ).json()["status"] == "received"
        assert client.post(
            f"/api/admin/returns/{ret['id']}/complete", headers=AUTH(admin_token)
        ).json()["status"] == "completed"

        result = client.post(
            f"/api/admin/returns/{ret['id']}/refund", headers=AUTH(admin_token)
        )
        assert result.status_code == 200, result.text
        refund = result.json()["refund"]
        assert refund["status"] == "completed"

        got = client.get(f"/api/orders/{order['id']}", headers=AUTH(customer_token)).json()
        # Refund covers the returned line value only (tax/shipping are not refunded).
        assert got["payment_status"] == "partially_refunded"

    def test_cannot_return_more_than_purchased(
        self, client, seller_token, customer_token, admin_token, category
    ):
        order = self._delivered_order(
            client, seller_token, customer_token, admin_token, category
        )
        r = client.post(
            "/api/returns",
            json={
                "order_id": order["id"],
                "reason": "too many",
                "items": [{"order_item_id": order["items"][0]["id"], "quantity": 99}],
            },
            headers=AUTH(customer_token),
        )
        assert r.status_code == 400

    def test_customer_cancel_return(
        self, client, seller_token, customer_token, admin_token, category
    ):
        order = self._delivered_order(
            client, seller_token, customer_token, admin_token, category
        )
        ret = client.post(
            "/api/returns",
            json={
                "order_id": order["id"],
                "reason": "no longer needed",
                "items": [{"order_item_id": order["items"][0]["id"], "quantity": 1}],
            },
            headers=AUTH(customer_token),
        ).json()
        r = client.post(
            f"/api/returns/{ret['id']}/cancel", headers=AUTH(customer_token)
        )
        assert r.status_code == 200
        assert r.json()["status"] == "cancelled"

    def test_non_admin_cannot_moderate_returns(
        self, client, seller_token, customer_token, admin_token, category
    ):
        order = self._delivered_order(
            client, seller_token, customer_token, admin_token, category
        )
        ret = client.post(
            "/api/returns",
            json={
                "order_id": order["id"],
                "reason": "moderation test",
                "items": [{"order_item_id": order["items"][0]["id"], "quantity": 1}],
            },
            headers=AUTH(customer_token),
        ).json()
        r = client.post(
            f"/api/admin/returns/{ret['id']}/approve", headers=AUTH(seller_token)
        )
        assert r.status_code == 403


# ---------------------------------------------------------------------------
# 8. Reviews: verified purchase comes from order data
# ---------------------------------------------------------------------------

class TestReviewVerification:
    def test_paid_but_undelivered_review_not_verified(
        self, client, seller_token, customer_token, category
    ):
        product = make_product(client, seller_token, category, price="25.00")
        buy(client, customer_token, product)  # paid, confirmed — not delivered
        r = client.post(
            f"/api/products/{product['id']}/reviews",
            json={"rating": 4, "comment": "good so far"},
            headers=AUTH(customer_token),
        )
        assert r.status_code == 201, r.text
        assert r.json()["is_verified"] is False

    def test_verified_flag_true_after_delivery(
        self, client, seller_token, customer_token, admin_token, category
    ):
        product = make_product(client, seller_token, category, price="25.00")
        add_to_cart(client, customer_token, product["id"], qty=1)
        order = checkout(client, customer_token).json()
        pay_success(client, customer_token, order["id"])
        advance_to_delivered(client, admin_token, order["id"])

        r = client.post(
            f"/api/products/{product['id']}/reviews",
            json={"rating": 5, "comment": "arrived and works"},
            headers=AUTH(customer_token),
        )
        assert r.status_code == 201, r.text
        assert r.json()["is_verified"] is True
        # Still pending moderation → not counted in the public aggregate.
        assert r.json()["moderation_status"] == "pending"


# ---------------------------------------------------------------------------
# 9. Address book + immutable order snapshot
# ---------------------------------------------------------------------------

class TestAddressSnapshot:
    def test_order_address_snapshot_is_immutable(
        self, client, seller_token, customer_token, category
    ):
        product = make_product(client, seller_token, category, price="15.00")
        addr = client.post(
            "/api/addresses",
            json={
                "recipient_name": "Original Name",
                "line1": "1 Original Lane",
                "city": "Oldtown",
                "postal_code": "111111",
                "country": "India",
                "is_default": True,
            },
            headers=AUTH(customer_token),
        )
        assert addr.status_code == 201, addr.text
        addr_id = addr.json()["id"]

        add_to_cart(client, customer_token, product["id"])
        order = checkout(client, customer_token, shipping_address_id=addr_id).json()
        assert "1 Original Lane" in order["shipping_address"]
        snapshot_before = order["shipping_address_snapshot"]

        # Edit the address-book entry — the historical order must not change.
        upd = client.put(
            f"/api/addresses/{addr_id}",
            json={"line1": "999 Changed Road", "city": "Newville"},
            headers=AUTH(customer_token),
        )
        assert upd.status_code == 200, upd.text

        got = client.get(f"/api/orders/{order['id']}", headers=AUTH(customer_token)).json()
        assert got["shipping_address_snapshot"] == snapshot_before
        assert "Original Lane" in got["shipping_address"]
        assert "Changed Road" not in got["shipping_address"]

    def test_address_book_crud_and_default(
        self, client, customer_token
    ):
        r = client.post(
            "/api/addresses",
            json={
                "recipient_name": "Addr One",
                "line1": "10 First St",
                "city": "Metro",
                "postal_code": "123456",
                "country": "India",
            },
            headers=AUTH(customer_token),
        )
        assert r.status_code == 201
        first = r.json()

        second = client.post(
            "/api/addresses",
            json={
                "recipient_name": "Addr Two",
                "line1": "20 Second St",
                "city": "Metro",
                "postal_code": "654321",
                "country": "India",
            },
            headers=AUTH(customer_token),
        ).json()

        marked = client.put(
            f"/api/addresses/{second['id']}/default", headers=AUTH(customer_token)
        )
        assert marked.status_code == 200
        assert marked.json()["is_default"] is True

        listed = client.get("/api/addresses", headers=AUTH(customer_token)).json()
        defaults = [a for a in listed if a["is_default"]]
        assert len(defaults) == 1
        assert defaults[0]["id"] == second["id"]

        deleted = client.delete(
            f"/api/addresses/{first['id']}", headers=AUTH(customer_token)
        )
        assert deleted.status_code == 204
        remaining = [a["id"] for a in client.get("/api/addresses", headers=AUTH(customer_token)).json()]
        assert first["id"] not in remaining


# ---------------------------------------------------------------------------
# 10. Shipping catalog
# ---------------------------------------------------------------------------

class TestShippingMethods:
    def test_list_shipping_methods_is_public(self, client):
        r = client.get("/api/shipping/methods")
        assert r.status_code == 200
        codes = {m["code"] for m in r.json()}
        assert {"standard", "express", "priority"} <= codes
        for method in r.json():
            assert Decimal(method["charge"]) > 0
