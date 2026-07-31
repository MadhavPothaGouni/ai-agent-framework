def _signup_and_get_token(client, email="chat@example.com", password="secret123"):
    resp = client.post("/auth/signup", json={"email": email, "password": password})
    return resp.json()["access_token"]


def test_chat_without_token_rejected(client):
    resp = client.post("/chat", json={"message": "hello"})
    assert resp.status_code == 401


def test_chat_with_token_returns_reply_and_session_id(client):
    token = _signup_and_get_token(client)

    resp = client.post(
        "/chat",
        json={"message": "hello"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["reply"]  # non-empty
    assert body["session_id"]  # server-generated session id


def test_chat_reuses_session_id_when_provided(client):
    token = _signup_and_get_token(client, email="session@example.com")
    headers = {"Authorization": f"Bearer {token}"}

    first = client.post("/chat", json={"message": "hi"}, headers=headers).json()
    session_id = first["session_id"]

    second = client.post(
        "/chat",
        json={"message": "still here", "session_id": session_id},
        headers=headers,
    ).json()

    assert second["session_id"] == session_id