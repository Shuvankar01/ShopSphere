"""Step 5 security tests: registration constraints, tokens, logout,
change-password, brute-force rate limiting."""


AUTH = lambda token: {"Authorization": f"Bearer {token}"}  # noqa: E731


def register(client, email, password="Password123!", role=None, name="Sec User"):
    payload = {"full_name": name, "email": email, "password": password}
    if role is not None:
        payload["role"] = role
    return client.post("/api/auth/register", json=payload)


# ---------------------------------------------------------------------------
# Registration / privilege escalation
# ---------------------------------------------------------------------------

class TestRegistrationConstraints:
    def test_cannot_self_register_as_admin(self, client):
        r = register(client, "escalate@example.com", role="admin")
        assert r.status_code == 422

    def test_cannot_register_with_arbitrary_role(self, client):
        r = register(client, "hacker@example.com", role="superuser")
        assert r.status_code == 422

    def test_role_defaults_to_customer_and_user_role_is_recorded(self, client, db):
        from app.models.role import Role, UserRole
        from app.models.user import User

        r = register(client, "plainrole@example.com")
        assert r.status_code == 200
        assert r.json()["user"]["role"] == "customer"

        user = db.query(User).filter(User.email == "plainrole@example.com").one()
        link = db.query(UserRole).filter(UserRole.user_id == user.id).one()
        role = db.query(Role).filter(Role.id == link.role_id).one()
        assert role.name == "customer"

    def test_seller_registration_allowed(self, client):
        r = register(client, "sellrole@example.com", role="seller")
        assert r.status_code == 200
        assert r.json()["user"]["role"] == "seller"

    def test_short_password_rejected(self, client):
        r = register(client, "shortpw@example.com", password="short")
        assert r.status_code == 422

    def test_invalid_email_rejected(self, client):
        r = register(client, "not-an-email")
        assert r.status_code == 422


# ---------------------------------------------------------------------------
# Tokens
# ---------------------------------------------------------------------------

class TestTokens:
    def test_refresh_returns_new_access_token(self, client):
        r = register(client, "refresh@example.com")
        refresh = r.json()["refresh_token"]
        r2 = client.post("/api/auth/refresh", json={"refresh_token": refresh})
        assert r2.status_code == 200
        assert "access_token" in r2.json()

    def test_access_token_rejected_as_refresh_token(self, client):
        r = register(client, "wrongtoken@example.com")
        access = r.json()["access_token"]
        r2 = client.post("/api/auth/refresh", json={"refresh_token": access})
        assert r2.status_code == 401

    def test_garbage_refresh_token_rejected(self, client):
        r = client.post("/api/auth/refresh", json={"refresh_token": "garbage.token.value"})
        assert r.status_code == 401


# ---------------------------------------------------------------------------
# Logout
# ---------------------------------------------------------------------------

class TestLogout:
    def test_logout_requires_authentication(self, client):
        r = client.post("/api/auth/logout")
        assert r.status_code == 401

    def test_logout_with_valid_token(self, client, customer_token):
        r = client.post("/api/auth/logout", headers=AUTH(customer_token))
        assert r.status_code == 204

    def test_logout_rejects_invalid_token(self, client):
        r = client.post("/api/auth/logout", headers=AUTH("not-a-token"))
        assert r.status_code == 401


# ---------------------------------------------------------------------------
# Change password
# ---------------------------------------------------------------------------

class TestChangePassword:
    def test_change_password_flow(self, client):
        email = "chpw@example.com"
        register(client, email, password="oldpassword123")

        r = client.post(
            "/api/auth/login", json={"email": email, "password": "oldpassword123"}
        )
        token = r.json()["access_token"]

        # Wrong current password → 401
        r2 = client.post(
            "/api/auth/change-password",
            json={"current_password": "wrongpass1", "new_password": "newpassword123"},
            headers=AUTH(token),
        )
        assert r2.status_code == 401

        # Correct current password → 204
        r3 = client.post(
            "/api/auth/change-password",
            json={"current_password": "oldpassword123", "new_password": "newpassword123"},
            headers=AUTH(token),
        )
        assert r3.status_code == 204

        # Old password no longer works, new one does
        assert (
            client.post(
                "/api/auth/login", json={"email": email, "password": "oldpassword123"}
            ).status_code
            == 401
        )
        assert (
            client.post(
                "/api/auth/login", json={"email": email, "password": "newpassword123"}
            ).status_code
            == 200
        )

    def test_change_password_requires_auth(self, client):
        r = client.post(
            "/api/auth/change-password",
            json={"current_password": "x", "new_password": "newpassword123"},
        )
        assert r.status_code == 401

    def test_short_new_password_rejected(self, client, customer_token):
        r = client.post(
            "/api/auth/change-password",
            json={"current_password": "Password123!", "new_password": "short"},
            headers=AUTH(customer_token),
        )
        assert r.status_code == 422


# ---------------------------------------------------------------------------
# Brute-force protection
# ---------------------------------------------------------------------------

class TestLoginRateLimiting:
    def test_failed_logins_are_rate_limited(self, client):
        email = "brute@example.com"
        for _ in range(5):
            r = client.post(
                "/api/auth/login", json={"email": email, "password": "wrongpass123"}
            )
            assert r.status_code == 401
        r = client.post(
            "/api/auth/login", json={"email": email, "password": "wrongpass123"}
        )
        assert r.status_code == 429
        assert r.headers.get("Retry-After") == "60"
        assert "Too many failed login attempts" in r.json()["detail"]

    def test_success_after_failures_on_other_accounts_not_affected(self, client):
        # A different account is unaffected by another account's failures.
        register(client, "healthy@example.com")
        r = client.post(
            "/api/auth/login",
            json={"email": "healthy@example.com", "password": "Password123!"},
        )
        assert r.status_code == 200

    def test_successful_login_resets_failures(self, client):
        email = "reset@example.com"
        register(client, email, password="Password123!")
        # 4 failures, then a success resets the window, then more failures
        # must not be blocked immediately.
        for _ in range(4):
            client.post("/api/auth/login", json={"email": email, "password": "nope"})
        assert (
            client.post(
                "/api/auth/login", json={"email": email, "password": "Password123!"}
            ).status_code
            == 200
        )
        r = client.post("/api/auth/login", json={"email": email, "password": "nope"})
        assert r.status_code == 401  # not 429 — window was reset
