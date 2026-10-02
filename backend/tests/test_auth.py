def test_register_user(client):
    response = client.post(
        "/api/auth/register",
        json={
            "full_name": "Test User",
            "email": "test@example.com",
            "password": "testpassword123",
            "role": "customer"
        }
    )
    assert response.status_code == 200
    data = response.json()
    assert data["user"]["email"] == "test@example.com"
    assert "access_token" in data

def test_register_existing_user(client):
    # First registration
    client.post(
        "/api/auth/register",
        json={
            "full_name": "Test User",
            "email": "test_existing@example.com",
            "password": "testpassword123",
        }
    )
    
    # Second registration with same email
    response = client.post(
        "/api/auth/register",
        json={
            "full_name": "Another User",
            "email": "test_existing@example.com",
            "password": "newpassword123",
        }
    )
    assert response.status_code == 409
    assert response.json()["detail"] == "User with this email already exists"

def test_login_success(client):
    client.post(
        "/api/auth/register",
        json={
            "full_name": "Login User",
            "email": "login@example.com",
            "password": "testpassword123",
        }
    )
    
    response = client.post(
        "/api/auth/login",
        json={
            "email": "login@example.com",
            "password": "testpassword123"
        }
    )
    assert response.status_code == 200
    data = response.json()
    assert data["user"]["email"] == "login@example.com"
    assert "access_token" in data

def test_login_failure(client):
    response = client.post(
        "/api/auth/login",
        json={
            "email": "nonexistent@example.com",
            "password": "wrongpassword"
        }
    )
    assert response.status_code == 401
