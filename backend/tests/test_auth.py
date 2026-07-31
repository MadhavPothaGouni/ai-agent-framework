def test_signup_returns_token(client):
    resp = client.post("/auth/signup", json={"email": "a@example.com", "password": "secret123"})
    assert resp.status_code == 200
    assert "access_token" in resp.json()


def test_signup_duplicate_email_rejected(client):
    client.post("/auth/signup", json={"email": "dupe@example.com", "password": "secret123"})
    resp = client.post("/auth/signup", json={"email": "dupe@example.com", "password": "secret123"})
    assert resp.status_code == 400


def test_login_wrong_password_rejected(client):
    client.post("/auth/signup", json={"email": "b@example.com", "password": "correct-pw"})
    resp = client.post("/auth/login", json={"email": "b@example.com", "password": "wrong-pw"})
    assert resp.status_code == 401


def test_login_correct_password_returns_token(client):
    client.post("/auth/signup", json={"email": "c@example.com", "password": "correct-pw"})
    resp = client.post("/auth/login", json={"email": "c@example.com", "password": "correct-pw"})
    assert resp.status_code == 200
    assert "access_token" in resp.json()