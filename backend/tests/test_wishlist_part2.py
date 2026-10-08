"""Part 2 tests: wishlist edge handling (duplicates, inactive products,
move-to-cart respecting an applied coupon)."""


def _auth(token):
    return {"Authorization": f"Bearer {token}"}


def _make_coupon(client, admin_token, code="SAVE20"):
    r = client.post(
        "/api/coupons",
        json={"code": code, "discount_type": "percent", "discount_value": "20",
              "max_uses": 50},
        headers=_auth(admin_token),
    )
    assert r.status_code == 201, r.text
    return r.json()


def _product(client, seller_token, category, name="Wish Product", price="15.00", stock=10, sku=None):
    payload = {"name": name, "description": f"{name} description", "price": price,
               "stock": stock, "category_id": category["id"]}
    if sku:
        payload["sku"] = sku
    r = client.post("/api/products", json=payload, headers=_auth(seller_token))
    assert r.status_code == 201, r.text
    return r.json()


class TestWishlistEdges:
    def test_duplicate_add_conflicts(self, client, customer_token, product):
        ch = _auth(customer_token)
        r = client.post("/api/wishlist/add", json={"product_id": product["id"]}, headers=ch)
        assert r.status_code == 201
        r = client.post("/api/wishlist/add", json={"product_id": product["id"]}, headers=ch)
        assert r.status_code == 409
        # Still exactly one entry.
        r = client.get("/api/wishlist", headers=ch)
        assert len(r.json()["items"]) == 1

    def test_inactive_product_cannot_be_added(self, client, customer_token, seller_token, category):
        p = _product(client, seller_token, category, name="Will Deactivate")
        client.put(
            f"/api/products/{p['id']}",
            json={"is_active": False},
            headers=_auth(seller_token),
        )
        r = client.post(
            "/api/wishlist/add", json={"product_id": p["id"]}, headers=_auth(customer_token)
        )
        assert r.status_code == 400
        assert "no longer available" in r.json()["detail"].lower()

    def test_missing_product_404(self, client, customer_token):
        r = client.post(
            "/api/wishlist/add", json={"product_id": "does-not-exist"},
            headers=_auth(customer_token),
        )
        assert r.status_code == 404

    def test_move_to_cart_removes_from_wishlist(self, client, customer_token, product):
        ch = _auth(customer_token)
        client.post("/api/wishlist/add", json={"product_id": product["id"]}, headers=ch)
        r = client.post(
            "/api/wishlist/move-to-cart",
            json={"product_id": product["id"], "quantity": 2},
            headers=ch,
        )
        assert r.status_code == 200, r.text
        body = r.json()
        # One line item holding quantity 2 (item_count counts distinct lines).
        assert body["item_count"] == 1
        assert body["items"][0]["quantity"] == 2

        wishlist = client.get("/api/wishlist", headers=ch).json()
        assert not any(i.get("product_id") == product["id"] for i in wishlist["items"])

    def test_move_to_cart_requires_positive_quantity(self, client, customer_token, product):
        ch = _auth(customer_token)
        client.post("/api/wishlist/add", json={"product_id": product["id"]}, headers=ch)
        r = client.post(
            "/api/wishlist/move-to-cart",
            json={"product_id": product["id"], "quantity": 0},
            headers=ch,
        )
        assert r.status_code == 400

    def test_move_to_cart_blocked_when_out_of_stock(self, client, customer_token, seller_token, category):
        p = _product(client, seller_token, category, name="Sold Out Soon", stock=1)
        ch = _auth(customer_token)
        client.post("/api/wishlist/add", json={"product_id": p["id"]}, headers=ch)

        # Someone else buys the only unit first.
        other = client.post(
            "/api/auth/register",
            json={"full_name": "Other Wish Customer", "email": "other.wish.cust@test.com",
                  "password": "Password123!", "role": "customer"},
        ).json()["access_token"]
        client.post("/api/cart/add", json={"product_id": p["id"], "quantity": 1},
                    headers=_auth(other))
        r = client.post(
            "/api/orders/create",
            json={"shipping_address": "1 Test Rd", "payment_method": "card"},
            headers=_auth(other),
        )
        assert r.status_code == 201, r.text

        r = client.post(
            "/api/wishlist/move-to-cart",
            json={"product_id": p["id"], "quantity": 1},
            headers=ch,
        )
        assert r.status_code == 400
        assert "insufficient" in r.json()["detail"].lower()
        # Item stays in the wishlist so the customer can retry later.
        wishlist = client.get("/api/wishlist", headers=ch).json()
        assert any(i.get("product_id") == p["id"] for i in wishlist["items"])

    def test_inactive_product_cannot_be_moved(self, client, customer_token, seller_token, category):
        p = _product(client, seller_token, category, name="Deactivate After Wish")
        ch = _auth(customer_token)
        client.post("/api/wishlist/add", json={"product_id": p["id"]}, headers=ch)
        client.put(
            f"/api/products/{p['id']}",
            json={"is_active": False},
            headers=_auth(seller_token),
        )
        r = client.post(
            "/api/wishlist/move-to-cart",
            json={"product_id": p["id"], "quantity": 1},
            headers=ch,
        )
        assert r.status_code == 400
        assert "no longer available" in r.json()["detail"].lower()

    def test_moved_items_respect_applied_coupon(self, client, admin_token, customer_token,
                                                seller_token, category):
        a = _product(client, seller_token, category, name="Coupon A", price="50.00")
        b = _product(client, seller_token, category, name="Coupon B", price="25.00", sku="WB-SKU-1")
        _make_coupon(client, admin_token)

        ch = _auth(customer_token)
        client.post("/api/cart/add", json={"product_id": a["id"], "quantity": 2}, headers=ch)
        r = client.post("/api/cart/coupon", json={"code": "SAVE20"}, headers=ch)
        assert r.status_code == 200
        before = r.json()
        assert before["coupon_code"] == "SAVE20"

        client.post("/api/wishlist/add", json={"product_id": b["id"]}, headers=ch)
        r = client.post(
            "/api/wishlist/move-to-cart",
            json={"product_id": b["id"], "quantity": 1},
            headers=ch,
        )
        assert r.status_code == 200, r.text
        body = r.json()
        # Moved item bumps the subtotal and the discount is recomputed on top.
        assert body["coupon_code"] == "SAVE20"
        assert float(body["discount_amount"]) > float(before["discount_amount"])
        assert float(body["total"]) == float(body["subtotal"]) - float(body["discount_amount"])
        # The moved product is gone from the wishlist but remains orderable.
        assert not any(i.get("product_id") == b["id"]
                       for i in client.get("/api/wishlist", headers=ch).json()["items"])

    def test_requires_auth(self, client, product):
        assert client.post(
            "/api/wishlist/add", json={"product_id": product["id"]}
        ).status_code == 401
        assert client.get("/api/wishlist").status_code == 401
