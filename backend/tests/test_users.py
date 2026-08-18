from fastapi.testclient import TestClient


def test_create_user_returns_user_payload(client: TestClient):
    response = client.post("/users", json={"name": "Alice", "wallet_name": "alice"})

    assert response.status_code == 201
    assert response.json()["name"] == "Alice"
    assert response.json()["wallet_name"] == "alice"
    assert isinstance(response.json()["id"], int)


def test_list_users_includes_created_user(client: TestClient):
    client.post("/users", json={"name": "Bob", "wallet_name": "bob"})

    response = client.get("/users")

    assert response.status_code == 200
    assert {"id": 1, "name": "Bob", "wallet_name": "bob"} in response.json()
