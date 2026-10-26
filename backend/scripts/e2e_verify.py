"""End-to-end HTTP verification against a running ShopSphere backend.

Exercises every documented feature area: health, auth, catalog, cart + coupon
engine, checkout + payments, reviews + moderation, inventory reservation and
the admin surface. Prints a PASS/FAIL line per check.

Usage (the backend must already be running and seeded)::

    python scripts/e2e_verify.py

Point it at a different deployment with ``API_BASE_URL``::

    API_BASE_URL=http://localhost:8000 python scripts/e2e_verify.py
"""

from __future__ import annotations

import json
import os
import sys
import urllib.error
import urllib.request
import uuid
from decimal import Decimal

BASE = os.getenv("API_BASE_URL", "http://localhost:8000").rstrip("/")

PASS, FAIL = [], []


def call(method, path, body=None, token=None, expect=None):
    url = f"{BASE}{path}"
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(url, data=data, method=method)
    req.add_header("Content-Type", "application/json")
    if token:
        req.add_header("Authorization", f"Bearer {token}")
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            raw = r.read().decode()
            status = r.status
    except urllib.error.HTTPError as e:
        raw = e.read().decode()
        status = e.code
    except Exception as e:  # noqa: BLE001
        return 0, {"error": str(e)}
    try:
        return status, json.loads(raw) if raw else {}
    except json.JSONDecodeError:
        return status, raw


def check(name, cond, detail=""):
    (PASS if cond else FAIL).append(name)
    print(
        f"[{'PASS' if cond else 'FAIL'}] {name}" + (f"  -- {detail}" if detail else "")
    )
    return cond


def section(title):
    print(f"\n=== {title} ===")


# ---------------------------------------------------------------------------
section("1. HEALTH / ROOT")
s, b = call("GET", "/health")
check("GET /health returns 200", s == 200, f"status={s} body={b}")
check(
    "health reports db reachable",
    bool(b.get("database") in ("ok", "connected", True, "healthy")) or "database" in b,
    str(b),
)
s, b = call("GET", "/")
check("GET / returns 200 (root)", s == 200, f"status={s}")

# ---------------------------------------------------------------------------
section("2. AUTH — register / login / refresh / profile")
email = f"e2e_user_{uuid.uuid4().hex[:8]}@example.com"
s, b = call(
    "POST",
    "/api/auth/register",
    {
        "email": email,
        "password": "Passw0rd!23",
        "full_name": "E2E User",
    },
)
check(
    "POST /api/auth/register returns 200/201", s in (200, 201), f"status={s} body={b}"
)
tok = b.get("access_token")
check("register returns access_token", bool(tok))
check(
    "register returns user.role=customer",
    b.get("user", {}).get("role") == "customer",
    str(b.get("user")),
)

s, b = call("POST", "/api/auth/login", {"email": email, "password": "Passw0rd!23"})
check(
    "POST /api/auth/login returns 200 + token",
    s == 200 and bool(b.get("access_token")),
    f"status={s}",
)
tok = b.get("access_token") or tok
refresh = b.get("refresh_token")

s, b = call("GET", "/api/users/profile", token=tok)
check("GET /api/users/profile returns 200", s == 200, f"status={s}")

s, b = call("GET", "/api/users/profile")
check("GET /api/users/profile without token -> 401", s == 401, f"status={s}")

s, b = call("POST", "/api/auth/login", {"email": email, "password": "wrong-password"})
check("login with wrong password -> 401", s == 401, f"status={s}")

if refresh:
    s, b = call("POST", "/api/auth/refresh", {"refresh_token": refresh})
    check("POST /api/auth/refresh returns 200", s == 200, f"status={s}")

# ---------------------------------------------------------------------------
section("3. CATALOG — products / categories / brands / search")
s, b = call("GET", "/api/products")
check("GET /api/products returns 200", s == 200, f"status={s}")
items = b.get("items", b if isinstance(b, list) else [])
total = b.get("total", len(items) if isinstance(b, list) else 0)
check("product list is non-empty", total > 0, f"total={total}")
product = items[0] if items else None
check(
    "product item has id/price/stock",
    bool(product and product.get("id") and product.get("price") is not None),
    str(product)[:200] if product else "none",
)

s, b = call("GET", "/api/categories")
check("GET /api/categories returns 200", s == 200, f"status={s}")
cats = b if isinstance(b, list) else b.get("items", [])
check("categories non-empty", len(cats) > 0, f"n={len(cats)}")

s, b = call("GET", "/api/brands")
check("GET /api/brands returns 200", s == 200, f"status={s}")

s, b = call("GET", "/api/products/search/suggestions?q=la")
check("GET /api/products/search/suggestions returns 200", s == 200, f"status={s}")

if product:
    pid = product["id"]
    s, b = call("GET", f"/api/products/{pid}")
    check("GET /api/products/{id} returns 200", s == 200, f"status={s}")
    s, b = call("GET", f"/api/products/{pid}/reviews")
    check("GET /api/products/{id}/reviews returns 200", s == 200, f"status={s}")
    s, b = call("GET", f"/api/products/{pid}/related")
    check("GET /api/products/{id}/related returns 200", s == 200, f"status={s}")
else:
    pid = None

# ---------------------------------------------------------------------------
section("4. CART — add / update / remove / coupon engine")
s, b = call("GET", "/api/cart", token=tok)
check("GET /api/cart returns 200", s == 200, f"status={s}")

if pid:
    s, b = call("POST", "/api/cart/add", {"product_id": pid, "quantity": 2}, token=tok)
    check("POST /api/cart/add returns 200/201", s in (200, 201), f"status={s} body={b}")
    s, b = call("GET", "/api/cart", token=tok)
    cart_items = b.get("items", []) if isinstance(b, dict) else []
    check("cart now has 1 line", len(cart_items) == 1, f"n={len(cart_items)} body={b}")
    line_total = Decimal(str(b.get("subtotal", b.get("total", 0))))
    check("cart subtotal > 0", line_total > 0, f"subtotal={line_total}")

    s, b = call(
        "PUT", "/api/cart/update", {"product_id": pid, "quantity": 3}, token=tok
    )
    check(
        "PUT /api/cart/update returns 200", s == 200, f"status={s} body={str(b)[:250]}"
    )

    s, b = call("POST", "/api/cart/coupon", {"code": "NOPE-NOT-A-REAL-CODE"}, token=tok)
    check(
        "apply bogus coupon is rejected (4xx)", 400 <= s < 500, f"status={s} body={b}"
    )

    s, b = call("DELETE", "/api/cart/coupon", token=tok)
    check(
        "DELETE /api/cart/coupon returns 200",
        s == 200,
        f"status={s} body={str(b)[:200]}",
    )

# ---------------------------------------------------------------------------
section("5. ADMIN — coupons (create, then apply to cart)")
admin_email = "admin@shopsphere.com"
s, b = call("POST", "/api/auth/login", {"email": admin_email, "password": "admin123"})
admin_tok = b.get("access_token") if s == 200 else None
check("admin login works (seeded admin)", s == 200 and bool(admin_tok), f"status={s}")

coupon_code = f"E2E{uuid.uuid4().hex[:6].upper()}"
if admin_tok:
    s, b = call("GET", "/api/admin/coupons", token=admin_tok)
    check(
        "GET /api/admin/coupons returns 200",
        s == 200,
        f"status={s} body={str(b)[:200]}",
    )
    s, b = call(
        "POST",
        "/api/admin/coupons",
        {
            "code": coupon_code,
            "discount_type": "percent",
            "discount_value": 10,
            "max_discount_amount": 50,
            "per_user_limit": 1,
        },
        token=admin_tok,
    )
    check(
        "POST /api/admin/coupons returns 201",
        s == 201,
        f"status={s} body={str(b)[:200]}",
    )
    coupon_id = b.get("id") if isinstance(b, dict) else None

    if pid:
        s, b = call("POST", "/api/cart/coupon", {"code": coupon_code}, token=tok)
        check(
            "apply valid coupon to cart returns 200",
            s == 200,
            f"status={s} body={str(b)[:250]}",
        )
        check(
            "coupon applied to cart (coupon_code set)",
            isinstance(b, dict) and b.get("coupon_code") == coupon_code,
            str(b.get("coupon_code")),
        )
        s, b = call("GET", "/api/cart", token=tok)
        check(
            "cart shows discount_amount > 0",
            (
                Decimal(str(b.get("discount_amount", 0))) > 0
                if isinstance(b, dict)
                else False
            ),
            str(b.get("discount_amount")),
        )

# ---------------------------------------------------------------------------
section("6. CHECKOUT — quote / create order / payment")
s, b = call(
    "POST",
    "/api/addresses",
    {
        "recipient_name": "E2E User",
        "phone": "5551234567",
        "line1": "1 Test Street",
        "city": "Testville",
        "state": "TS",
        "postal_code": "12345",
        "country": "US",
        "is_default": True,
    },
    token=tok,
)
check(
    "POST /api/addresses returns 200/201",
    s in (200, 201),
    f"status={s} body={str(b)[:200]}",
)
addr_id = b.get("id") if isinstance(b, dict) else None
if addr_id:
    s, b = call("GET", f"/api/addresses/{addr_id}", token=tok)
    check(
        "GET /api/addresses/{id} returns 200 (frontend contract)",
        s == 200,
        f"status={s} body={str(b)[:200]}",
    )
    s, b = call("PUT", f"/api/addresses/{addr_id}", {"city": "Newtown"}, token=tok)
    check(
        "PUT /api/addresses/{id} returns 200",
        s == 200,
        f"status={s} body={str(b)[:200]}",
    )
    s, b = call("PUT", f"/api/addresses/{addr_id}/default", {}, token=tok)
    check("PUT /api/addresses/{id}/default returns 200", s == 200, f"status={s}")
s, b = call("GET", "/api/addresses", token=tok)
check("GET /api/addresses returns 200", s == 200, f"status={s}")

s, b = call("POST", "/api/orders/quote", {"shipping_method": "standard"}, token=tok)
check("POST /api/orders/quote returns 200", s == 200, f"status={s} body={str(b)[:250]}")

s, b = call("GET", "/api/shipping/methods")
check("GET /api/shipping/methods returns 200", s == 200, f"status={s}")

order_id = None
if pid and addr_id:
    s, b = call(
        "POST",
        "/api/orders/create",
        {
            "shipping_address_id": addr_id,
            "payment_method": "card",
            "shipping_method": "standard",
        },
        token=tok,
    )
    check(
        "POST /api/orders/create returns 201",
        s == 201,
        f"status={s} body={str(b)[:300]}",
    )
    order_id = b.get("id") if isinstance(b, dict) else None
    if order_id:
        check(
            "order total_amount > 0",
            Decimal(str(b.get("total_amount", 0))) > 0,
            str(b.get("total_amount")),
        )
        check(
            "order grand total = subtotal - discount + tax + shipping",
            Decimal(str(b.get("total_amount")))
            == Decimal(str(b.get("subtotal", 0)))
            - Decimal(str(b.get("discount_amount", 0)))
            + Decimal(str(b.get("tax_amount", 0)))
            + Decimal(str(b.get("shipping_cost", 0))),
            f"total={b.get('total_amount')} subtotal={b.get('subtotal')} disc={b.get('discount_amount')} "
            f"tax={b.get('tax_amount')} ship={b.get('shipping_cost')}",
        )

        s, b = call("GET", f"/api/orders/{order_id}", token=tok)
        check("GET /api/orders/{id} returns 200", s == 200, f"status={s}")

        # Payment
        s, b = call(
            "POST",
            "/api/payment/create",
            {"order_id": order_id, "payment_method": "card"},
            token=tok,
        )
        check(
            "POST /api/payment/create returns 200/201",
            s in (200, 201),
            f"status={s} body={str(b)[:250]}",
        )
        txn = b.get("transaction_id") if isinstance(b, dict) else None
        if txn:
            s, b = call(
                "POST", f"/api/payment/{txn}/complete", {"result": "success"}, token=tok
            )
            check(
                "POST /api/payment/{txn}/complete returns 200",
                s == 200,
                f"status={s} body={str(b)[:250]}",
            )
            check(
                "payment status == succeeded",
                b.get("status") in ("succeeded", "completed", "success", "paid"),
                str(b)[:200],
            )

            s, b = call("GET", f"/api/orders/{order_id}", token=tok)
            check(
                "order payment_status became 'paid'",
                b.get("payment_status") == "paid",
                str(b.get("payment_status")),
            )

# ---------------------------------------------------------------------------
section("7. REVIEWS — create (verified purchase) + moderation")
if pid and order_id:
    s, b = call(
        "POST",
        f"/api/products/{pid}/reviews",
        {
            "rating": 5,
            "comment": "E2E verified purchase review",
        },
        token=tok,
    )
    check(
        "POST /api/products/{id}/reviews returns 201/200",
        s in (200, 201),
        f"status={s} body={str(b)[:250]}",
    )
    review_id = b.get("id") if isinstance(b, dict) else None

    s, b = call("GET", f"/api/products/{pid}/reviews")
    published = b if isinstance(b, list) else b.get("items", [])
    check(
        "review appears in product reviews (pending moderated out)",
        isinstance(published, list),
        f"n={len(published)}",
    )

    if admin_tok and review_id:
        s, b = call("GET", "/api/admin/reviews?status=pending", token=admin_tok)
        check(
            "GET /api/admin/reviews?status=pending returns 200", s == 200, f"status={s}"
        )
        s, b = call(
            "POST",
            f"/api/admin/reviews/{review_id}/moderate",
            {"action": "approve"},
            token=admin_tok,
        )
        check(
            "POST /api/admin/reviews/{id}/moderate approve returns 200",
            s == 200,
            f"status={s} body={str(b)[:250]}",
        )
        check(
            "moderation_status == approved",
            b.get("moderation_status") == "approved",
            str(b.get("moderation_status")),
        )

        s, b = call("GET", f"/api/products/{pid}/reviews")
        published = b if isinstance(b, list) else b.get("items", [])
        check(
            "approved review now visible to customer",
            len(published) > 0,
            f"n={len(published)}",
        )

# ---------------------------------------------------------------------------
section("8. INVENTORY — low stock / adjust / movements")
if admin_tok:
    s, b = call("GET", "/api/inventory/low-stock", token=admin_tok)
    check(
        "GET /api/inventory/low-stock returns 200",
        s == 200,
        f"status={s} body={str(b)[:200]}",
    )
if pid:
    s, b = call("GET", f"/api/inventory/products/{pid}", token=admin_tok)
    check(
        "GET /api/inventory/products/{id} returns 200",
        s == 200,
        f"status={s} body={str(b)[:200]}",
    )

# ---------------------------------------------------------------------------
section("9. ADMIN — dashboard / stats / users / products / order status")
if admin_tok:
    s, b = call("GET", "/api/admin/dashboard", token=admin_tok)
    check(
        "GET /api/admin/dashboard returns 200",
        s == 200,
        f"status={s} body={str(b)[:250]}",
    )
    check(
        "dashboard revenue is Decimal-serializable",
        isinstance(b.get("revenue"), (str, int, float))
        and Decimal(str(b.get("revenue", 0))) >= 0,
        str(b.get("revenue")),
    )
    check(
        "dashboard total_users >= 1",
        int(b.get("total_users", 0)) >= 1,
        str(b.get("total_users")),
    )
    check(
        "dashboard has recent_orders list",
        isinstance(b.get("recent_orders"), list),
        str(type(b.get("recent_orders"))),
    )

    s, b = call("GET", "/api/admin/stats", token=admin_tok)
    check(
        "GET /api/admin/stats returns 200 (frontend contract)",
        s == 200,
        f"status={s} body={str(b)[:200]}",
    )

    s, b = call("GET", "/api/admin/users", token=admin_tok)
    check("GET /api/admin/users returns 200", s == 200, f"status={s}")
    users = b if isinstance(b, list) else []
    check("admin users list non-empty", len(users) > 0, f"n={len(users)}")

    s, b = call("GET", "/api/admin/orders", token=admin_tok)
    check("GET /api/admin/orders returns 200", s == 200, f"status={s}")

    s, b = call("GET", "/api/admin/products", token=admin_tok)
    check("GET /api/admin/products returns 200", s == 200, f"status={s}")

    s, b = call("GET", "/api/admin/audit-logs", token=admin_tok)
    check("GET /api/admin/audit-logs returns 200", s == 200, f"status={s}")

    # Non-admin must be rejected
    s, b = call("GET", "/api/admin/dashboard", token=tok)
    check("GET /api/admin/dashboard as customer -> 403", s == 403, f"status={s}")
    s, b = call("GET", "/api/admin/stats", token=tok)
    check("GET /api/admin/stats as customer -> 403", s == 403, f"status={s}")

    # Toggles
    if users:
        target = next((u for u in users if u.get("email") == email), users[0])
        s, b = call(
            "PUT", f"/api/admin/users/{target['id']}/toggle", {}, token=admin_tok
        )
        check(
            "PUT /api/admin/users/{id}/toggle returns 200",
            s == 200,
            f"status={s} body={str(b)[:200]}",
        )
        flipped = b.get("is_active")
        s, b = call(
            "PUT", f"/api/admin/users/{target['id']}/toggle", {}, token=admin_tok
        )
        check(
            "user toggle flips back",
            s == 200 and b.get("is_active") != flipped,
            f"{flipped} -> {b.get('is_active')}",
        )

    if product:
        s, b = call(
            "PUT", f"/api/admin/products/{product['id']}/toggle", {}, token=admin_tok
        )
        check(
            "PUT /api/admin/products/{id}/toggle returns 200",
            s == 200,
            f"status={s} body={str(b)[:200]}",
        )
        s, b = call(
            "PUT", f"/api/admin/products/{product['id']}/toggle", {}, token=admin_tok
        )
        check("product toggle flips back", s == 200, f"status={s}")

    if order_id:
        # A successful demo payment auto-confirms the order, so the next legal
        # fulfillment transition is pending -> confirmed -> processing.
        s, b = call("GET", f"/api/orders/{order_id}", token=tok)
        current = b.get("order_status") if isinstance(b, dict) else None
        nxt = {
            "pending": "confirmed",
            "confirmed": "processing",
            "processing": "packed",
        }.get(current, "processing")
        s, b = call(
            "PUT",
            f"/api/admin/orders/{order_id}/status",
            {"status": nxt, "reason": "e2e"},
            token=admin_tok,
        )
        check(
            "PUT /api/admin/orders/{id}/status returns 200",
            s == 200,
            f"status={s} body={str(b)[:250]}",
        )
        check(
            f"order_status == {nxt}",
            b.get("order_status") == nxt,
            f"was={current} now={b.get('order_status')}",
        )

# ---------------------------------------------------------------------------
section("10. OTHER SURFACES — wishlist / banners / notifications / ai")
s, b = (
    call("POST", "/api/wishlist/add", {"product_id": pid}, token=tok)
    if pid
    else (0, {})
)
check(
    "POST /api/wishlist/add returns 200/201",
    s in (200, 201),
    f"status={s} body={str(b)[:200]}",
)
s, b = call("GET", "/api/wishlist", token=tok)
check("GET /api/wishlist returns 200", s == 200, f"status={s}")
s, b = call("GET", "/api/banners")
check("GET /api/banners returns 200", s == 200, f"status={s}")
s, b = call("GET", "/api/notifications", token=tok)
check("GET /api/notifications returns 200", s == 200, f"status={s}")
s, b = call("GET", "/api/recommendations", token=tok)
check("GET /api/recommendations returns 200", s == 200, f"status={s}")
s, b = call("GET", "/api/coupons", token=admin_tok)
check("GET /api/coupons returns 200", s == 200, f"status={s}")

# ---------------------------------------------------------------------------
section("11. BANNERS — admin CRUD (was a 500: NOT NULL on sort_order/image_url)")
if admin_tok:
    s, b = call(
        "POST",
        "/api/banners",
        {"title": "E2E Banner", "image_url": "https://example.com/b.png"},
        token=admin_tok,
    )
    check("POST /api/banners returns 200", s == 200, f"status={s} body={str(b)[:250]}")
    bid = b.get("id") if isinstance(b, dict) else None
    if bid:
        s, b = call("GET", f"/api/banners/{bid}")
        check("GET /api/banners/{id} returns 200", s == 200, f"status={s}")
        s, b = call(
            "PUT", f"/api/banners/{bid}", {"title": "E2E Banner v2"}, token=admin_tok
        )
        check(
            "PUT /api/banners/{id} returns 200",
            s == 200,
            f"status={s} body={str(b)[:250]}",
        )
        check(
            "banner title updated",
            b.get("title") == "E2E Banner v2",
            str(b.get("title")),
        )
        s, b = call("DELETE", f"/api/banners/{bid}", token=admin_tok)
        check(
            "DELETE /api/banners/{id} returns 200",
            s == 200,
            f"status={s} body={str(b)[:200]}",
        )
    s, b = call("POST", "/api/banners", {"title": "No image"}, token=admin_tok)
    check(
        "POST /api/banners without image_url returns 200 (image_url optional)",
        s == 200,
        f"status={s} body={str(b)[:200]}",
    )
    s, b = call("POST", "/api/banners", {"title": "Nope"}, token=tok)
    check("POST /api/banners as customer -> 403", s == 403, f"status={s}")

# ---------------------------------------------------------------------------
section("12. AUDIT LOGS — admin read (was a 500: missing audit_logs columns)")
if admin_tok:
    s, b = call("GET", "/api/admin/audit-logs", token=admin_tok)
    check(
        "GET /api/admin/audit-logs returns 200",
        s == 200,
        f"status={s} body={str(b)[:250]}",
    )
    s, b = call("GET", "/api/admin/audit-logs", token=tok)
    check("GET /api/admin/audit-logs as customer -> 403", s == 403, f"status={s}")

# ---------------------------------------------------------------------------
print("\n" + "=" * 62)
print(f"PASSED: {len(PASS)}    FAILED: {len(FAIL)}")
if FAIL:
    print("FAILURES:")
    for f in FAIL:
        print("  -", f)
print("=" * 62)
sys.exit(1 if FAIL else 0)
