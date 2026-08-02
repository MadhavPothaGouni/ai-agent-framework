def _signup_and_get_token(client, email):
    resp = client.post("/auth/signup", json={"email": email, "password": "secret123"})
    return resp.json()["access_token"]


def test_status_requires_auth(client):
    resp = client.get("/budget/status")
    assert resp.status_code == 401


def test_status_defaults_to_default_cap_with_zero_spend(client):
    token = _signup_and_get_token(client, "budget-route-default@example.com")

    resp = client.get("/budget/status", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 200
    body = resp.json()
    assert body["spent_this_month_usd"] == 0.0
    assert body["exceeded"] is False
    assert body["monthly_cap_usd"] > 0


def test_set_limit_requires_auth(client):
    resp = client.put("/budget/limit", json={"monthly_cap_usd": 10.0})
    assert resp.status_code == 401


def test_set_limit_updates_status(client):
    token = _signup_and_get_token(client, "budget-route-set@example.com")
    headers = {"Authorization": f"Bearer {token}"}

    resp = client.put("/budget/limit", json={"monthly_cap_usd": 42.5}, headers=headers)
    assert resp.status_code == 200
    assert resp.json()["monthly_cap_usd"] == 42.5

    status_resp = client.get("/budget/status", headers=headers)
    assert status_resp.json()["monthly_cap_usd"] == 42.5


def test_set_limit_rejects_non_positive_amount(client):
    token = _signup_and_get_token(client, "budget-route-invalid@example.com")
    headers = {"Authorization": f"Bearer {token}"}

    resp = client.put("/budget/limit", json={"monthly_cap_usd": 0}, headers=headers)
    assert resp.status_code == 422

    resp2 = client.put("/budget/limit", json={"monthly_cap_usd": -5}, headers=headers)
    assert resp2.status_code == 422


def test_running_a_workflow_updates_budget_status(client):
    
    token = _signup_and_get_token(client, "budget-route-e2e@example.com")
    headers = {"Authorization": f"Bearer {token}"}

    client.put("/budget/limit", json={"monthly_cap_usd": 1.0}, headers=headers)

    run_resp = client.post("/workflow/run", json={"task": "build a calculator"}, headers=headers)
    assert run_resp.status_code == 200
    body = run_resp.json()
    # Mock provider is free, so this ordinary run should complete normally.
    assert body["final_decision"] == "approved"
    assert body["total_cost_usd"] == 0.0

    status_resp = client.get("/budget/status", headers=headers)
    assert status_resp.json()["exceeded"] is False