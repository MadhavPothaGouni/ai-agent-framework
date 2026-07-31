def test_workflow_run_without_token_rejected(client):
    resp = client.post("/workflow/run", json={"task": "build a calculator"})
    assert resp.status_code == 401


def test_workflow_run_with_token_returns_full_trace(client):
    signup = client.post(
        "/auth/signup", json={"email": "workflow@example.com", "password": "secret123"}
    )
    token = signup.json()["access_token"]

    resp = client.post(
        "/workflow/run",
        json={"task": "build a calculator"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200

    body = resp.json()
    agent_order = [s["agent"] for s in body["steps"]]
    assert agent_order == ["planner", "coder", "tester", "reviewer"]
    assert body["final_decision"] == "approved"
    assert body["attempts"] == 1