"""Regression tests for the admin surface and the address book.

These cover bugs that made the admin panel and the address book unusable:

* `require_admin` stringified the `UserRole.role` *relationship object*
  (`<app.models.role.Role object at 0x...>`) instead of reading `r.role.name`,
  so every privileged request was denied with 403 even for real admins.
* Two `AuditLog` model classes were mapped to the same `audit_logs` table; the
  merged column set referenced columns the migration never created, so
  `GET /api/admin/audit-logs` raised a 500.
* `banners.image_url` / `banners.sort_order` were NOT NULL in the database but
  absent from the model, so `POST /api/banners` raised a 500.
* A second `/api/admin/dashboard` route shadowed the real one and referenced
  non-existent `Order.grand_total` / `Order.status` columns (500).
* The frontend calls `/api/admin/stats`, `/api/admin/coupons`,
  `/api/admin/users/:id/toggle`, `/api/admin/products/:id/toggle`,
  `/api/admin/orders/:id/status` and `/api/addresses/:id` — none of which
  existed on the backend.
"""

AUTH = lambda token: {"Authorization": f"Bearer {token}"}  # noqa: E731


def register(
    client, email, password="Password123!", role="customer", name="Admin User"
):
    r = client.post(
        "/api/auth/register",
        json={
            "full_name": name,
            "email": email,
            "password": password,
            "role": role,
        },
    )
    assert r.status_code == 200, r.text
    return r.json()


class TestRoleResolution:
    """`require_admin` must read the role name, not the relationship object."""

    def test_admin_via_user_roles_mapping_only(self, client, db):
        """An admin whose `users.role` column is not 'admin' but who has an
        admin `user_roles` row must still be allowed through."""
        from app.models.role import Role, UserRole
        from app.models.user import User

        auth = register(client, "mapped_admin@test.com")
        user = db.query(User).filter(User.email == "mapped_admin@test.com").first()
        assert user is not None

        role = db.query(Role).filter(Role.name == "admin").first()
        if role is None:
            role = Role(name="admin", description="Full administrative access")
            db.add(role)
            db.flush()
        db.add(UserRole(user_id=user.id, role_id=role.id))
        db.commit()

        # The primary column still says 'customer' — only the mapping says admin.
        assert user.role == "customer"

        r = client.get("/api/admin/dashboard", headers=AUTH(auth["access_token"]))
        assert r.status_code == 200, r.text

    def test_customer_with_no_admin_role_is_denied(self, client, customer_token):
        r = client.get("/api/admin/dashboard", headers=AUTH(customer_token))
        assert r.status_code == 403

    def test_seller_with_no_admin_role_is_denied(self, client, seller_token):
        r = client.get("/api/admin/dashboard", headers=AUTH(seller_token))
        assert r.status_code == 403


class TestAdminDashboard:
    def test_dashboard_returns_admin_stats(self, client, admin_token):
        r = client.get("/api/admin/dashboard", headers=AUTH(admin_token))
        assert r.status_code == 200, r.text
        body = r.json()
        for key in (
            "total_users",
            "total_orders",
            "total_products",
            "revenue",
            "recent_orders",
        ):
            assert key in body, f"missing {key} in {body}"
        assert isinstance(body["recent_orders"], list)

    def test_stats_alias_matches_dashboard(self, client, admin_token):
        """The frontend admin panel reads `/api/admin/stats`."""
        dash = client.get("/api/admin/dashboard", headers=AUTH(admin_token))
        stats = client.get("/api/admin/stats", headers=AUTH(admin_token))
        assert dash.status_code == 200, dash.text
        assert stats.status_code == 200, stats.text
        assert stats.json()["revenue"] == dash.json()["revenue"]

    def test_stats_requires_admin(self, client, customer_token):
        assert (
            client.get("/api/admin/stats", headers=AUTH(customer_token)).status_code
            == 403
        )


class TestAdminMutations:
    def test_list_and_create_coupons(self, client, admin_token):
        r = client.get("/api/admin/coupons", headers=AUTH(admin_token))
        assert r.status_code == 200, r.text
        assert isinstance(r.json(), list)

        r = client.post(
            "/api/admin/coupons",
            json={
                "code": "ADMINALIAS10",
                "discount_type": "percent",
                "discount_value": 10,
                "per_user_limit": 1,
            },
            headers=AUTH(admin_token),
        )
        assert r.status_code == 201, r.text
        assert r.json()["code"] == "ADMINALIAS10"

    def test_coupons_require_admin(self, client, customer_token):
        assert (
            client.get("/api/admin/coupons", headers=AUTH(customer_token)).status_code
            == 403
        )
        assert (
            client.post(
                "/api/admin/coupons",
                json={
                    "code": "NOPE",
                    "discount_type": "percent",
                    "discount_value": 5,
                },
                headers=AUTH(customer_token),
            ).status_code
            == 403
        )

    def test_toggle_user_status(self, client, admin_token):
        auth = register(client, "toggle_user@test.com")
        uid = auth["user"]["id"]
        r = client.put(
            f"/api/admin/users/{uid}/toggle", json={}, headers=AUTH(admin_token)
        )
        assert r.status_code == 200, r.text
        assert r.json()["is_active"] is False
        r = client.put(
            f"/api/admin/users/{uid}/toggle", json={}, headers=AUTH(admin_token)
        )
        assert r.status_code == 200
        assert r.json()["is_active"] is True

    def test_toggle_product_status(self, client, admin_token, product):
        r = client.put(
            f"/api/admin/products/{product['id']}/toggle",
            json={},
            headers=AUTH(admin_token),
        )
        assert r.status_code == 200, r.text
        assert r.json()["is_active"] is False
        r = client.put(
            f"/api/admin/products/{product['id']}/toggle",
            json={},
            headers=AUTH(admin_token),
        )
        assert r.status_code == 200
        assert r.json()["is_active"] is True

    def test_admin_order_status_transition(self, client, admin_token, product):
        auth = register(client, "status_admin_user@test.com")
        tok = auth["access_token"]
        r = client.post(
            "/api/cart/add",
            json={"product_id": product["id"], "quantity": 1},
            headers=AUTH(tok),
        )
        assert r.status_code in (200, 201), r.text
        r = client.post(
            "/api/orders/create",
            json={
                "shipping_address": "1 Test Street, Testville",
                "payment_method": "card",
            },
            headers=AUTH(tok),
        )
        assert r.status_code == 201, r.text
        order_id = r.json()["id"]

        r = client.put(
            f"/api/admin/orders/{order_id}/status",
            json={"status": "confirmed", "reason": "paid"},
            headers=AUTH(admin_token),
        )
        assert r.status_code == 200, r.text
        assert r.json()["order_status"] == "confirmed"

    def test_toggles_require_admin(self, client, customer_token):
        assert (
            client.put(
                "/api/admin/users/x/toggle", json={}, headers=AUTH(customer_token)
            ).status_code
            == 403
        )
        assert (
            client.put(
                "/api/admin/products/x/toggle", json={}, headers=AUTH(customer_token)
            ).status_code
            == 403
        )
        assert (
            client.put(
                "/api/admin/orders/x/status",
                json={"status": "confirmed"},
                headers=AUTH(customer_token),
            ).status_code
            == 403
        )


class TestAuditLogs:
    def test_audit_logs_list_returns_200(self, client, admin_token):
        """The `audit_logs` table must have every column the model selects."""
        r = client.get("/api/admin/audit-logs", headers=AUTH(admin_token))
        assert r.status_code == 200, r.text
        assert isinstance(r.json(), list)

    def test_audit_logs_require_admin(self, client, customer_token):
        assert (
            client.get(
                "/api/admin/audit-logs", headers=AUTH(customer_token)
            ).status_code
            == 403
        )


class TestBanners:
    def test_create_banner_without_image_url(self, client, admin_token):
        """`image_url` is optional in the schema, so it must be nullable."""
        r = client.post(
            "/api/banners", json={"title": "No image"}, headers=AUTH(admin_token)
        )
        assert r.status_code == 200, r.text
        assert r.json()["title"] == "No image"
        assert r.json()["image_url"] is None

    def test_create_banner_with_image_url(self, client, admin_token):
        r = client.post(
            "/api/banners",
            json={
                "title": "With image",
                "image_url": "https://example.com/b.png",
            },
            headers=AUTH(admin_token),
        )
        assert r.status_code == 200, r.text
        banner_id = r.json()["id"]

        r = client.get(f"/api/banners/{banner_id}")
        assert r.status_code == 200

        r = client.put(
            f"/api/banners/{banner_id}",
            json={"title": "Updated"},
            headers=AUTH(admin_token),
        )
        assert r.status_code == 200, r.text
        assert r.json()["title"] == "Updated"

        r = client.delete(f"/api/banners/{banner_id}", headers=AUTH(admin_token))
        assert r.status_code == 200, r.text

    def test_banner_mutation_requires_admin(self, client, customer_token):
        assert (
            client.post(
                "/api/banners", json={"title": "Nope"}, headers=AUTH(customer_token)
            ).status_code
            == 403
        )


class TestAddressBook:
    def _create(self, client, token):
        r = client.post(
            "/api/addresses",
            json={
                "recipient_name": "Addr User",
                "phone": "5551234567",
                "line1": "1 Test Street",
                "city": "Testville",
                "state": "TS",
                "postal_code": "12345",
                "country": "US",
            },
            headers=AUTH(token),
        )
        assert r.status_code == 201, r.text
        return r.json()

    def test_get_single_address(self, client, customer_token):
        addr = self._create(client, customer_token)
        r = client.get(f"/api/addresses/{addr['id']}", headers=AUTH(customer_token))
        assert r.status_code == 200, r.text
        assert r.json()["id"] == addr["id"]

    def test_get_address_of_other_user_is_404(self, client, customer_token):
        addr = self._create(client, customer_token)
        other = register(client, "other_addr@test.com")
        r = client.get(
            f"/api/addresses/{addr['id']}", headers=AUTH(other["access_token"])
        )
        assert r.status_code == 404

    def test_get_address_requires_authentication(self, client, customer_token):
        addr = self._create(client, customer_token)
        assert client.get(f"/api/addresses/{addr['id']}").status_code == 401
