def test_chat_without_token_rejected(client):
    resp = client.post("/chat", json={"message": "hello"})
    assert resp.status_code == 401


def test_chat_with_token_echoes_message(client):
    signup = client.post("/auth/signup", json={"email": "chat@example.com", "password": "secret123"})
    token = signup.json()["access_token"]

    resp = client.post(
        "/chat",
        json={"message": "hello"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200
    assert resp.json()["reply"] == "echo: hello"