from fastapi.testclient import TestClient

def test_register_user(client: TestClient):
    response = client.post("/register", data={"email": "new@test.com", "password": "pass", "name": "New User"})
    assert response.status_code == 200
    assert response.headers["HX-Redirect"] == "/dashboard"

def test_login_success(client: TestClient, test_user):
    response = client.post("/login", data={"email": "test@example.com", "password": "password123"})
    assert response.status_code == 200
    assert response.headers["HX-Redirect"] == "/dashboard"

def test_login_failure(client: TestClient):
    response = client.post("/login", data={"email": "wrong@test.com", "password": "wrong"})
    assert response.status_code == 200
    assert "inválidas" in response.text
