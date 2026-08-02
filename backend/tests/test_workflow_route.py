def _signup_and_get_token(client, email):
    resp = client.post("/auth/signup", json={"email": email, "password": "secret123"})
    return resp.json()["access_token"]


def test_workflow_run_without_token_rejected(client):
    resp = client.post("/workflow/run", json={"task": "build a calculator"})
    assert resp.status_code == 401


def test_workflow_run_with_token_returns_full_trace(client):
    token = _signup_and_get_token(client, "workflow@example.com")

    resp = client.post(
        "/workflow/run",
        json={"task": "build a calculator"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200

    body = resp.json()
    agent_order = [s["agent"] for s in body["steps"]]
    assert agent_order == ["planner", "coder", "tester", "security_auditor", "reviewer"]
    assert body["final_decision"] == "approved"
    assert body["attempts"] == 1
    assert body["run_id"]  # non-empty


def test_workflow_runs_list_without_token_rejected(client):
    resp = client.get("/workflow/runs")
    assert resp.status_code == 401


def test_workflow_run_appears_in_runs_list(client):
    token = _signup_and_get_token(client, "workflow-list@example.com")
    headers = {"Authorization": f"Bearer {token}"}

    run_resp = client.post("/workflow/run", json={"task": "build a widget"}, headers=headers)
    run_id = run_resp.json()["run_id"]

    list_resp = client.get("/workflow/runs", headers=headers)
    assert list_resp.status_code == 200

    run_ids = [r["run_id"] for r in list_resp.json()]
    assert run_id in run_ids


def test_workflow_run_detail_matches_original_response(client):
    token = _signup_and_get_token(client, "workflow-detail@example.com")
    headers = {"Authorization": f"Bearer {token}"}

    run_resp = client.post("/workflow/run", json={"task": "build a gadget"}, headers=headers)
    original = run_resp.json()

    detail_resp = client.get(f"/workflow/runs/{original['run_id']}", headers=headers)
    assert detail_resp.status_code == 200

    detail = detail_resp.json()
    assert detail["task"] == "build a gadget"
    assert detail["final_decision"] == original["final_decision"]
    assert [s["agent"] for s in detail["steps"]] == [s["agent"] for s in original["steps"]]


def test_workflow_run_detail_unknown_id_returns_404(client):
    token = _signup_and_get_token(client, "workflow-404@example.com")
    headers = {"Authorization": f"Bearer {token}"}

    resp = client.get("/workflow/runs/does-not-exist", headers=headers)
    assert resp.status_code == 404


def test_workflow_run_detail_not_visible_to_other_user(client):
    owner_token = _signup_and_get_token(client, "workflow-owner@example.com")
    other_token = _signup_and_get_token(client, "workflow-other@example.com")

    run_resp = client.post(
        "/workflow/run",
        json={"task": "private task"},
        headers={"Authorization": f"Bearer {owner_token}"},
    )
    run_id = run_resp.json()["run_id"]

    resp = client.get(
        f"/workflow/runs/{run_id}", headers={"Authorization": f"Bearer {other_token}"}
    )
    assert resp.status_code == 404

def test_workflow_run_response_includes_cost_totals(client):
    token = _signup_and_get_token(client, "workflow-cost@example.com")

    resp = client.post(
        "/workflow/run",
        json={"task": "build a calculator"},
        headers={"Authorization": f"Bearer {token}"},
    )
    body = resp.json()

    assert "total_cost_usd" in body
    assert "total_tokens" in body
    assert body["total_cost_usd"] == 0.0  # mock provider is free
    assert body["total_tokens"] > 0


def test_workflow_runs_list_includes_cost_totals(client):
    token = _signup_and_get_token(client, "workflow-cost-list@example.com")
    headers = {"Authorization": f"Bearer {token}"}

    client.post("/workflow/run", json={"task": "build a widget"}, headers=headers)

    list_resp = client.get("/workflow/runs", headers=headers)
    summaries = list_resp.json()
    assert len(summaries) >= 1
    assert all("total_cost_usd" in s and "total_tokens" in s for s in summaries)


def test_workflow_blocked_by_budget_returns_200_with_budget_exceeded_decision(client, db_session):
   
    from app.models.usage import UsageRecord

    token = _signup_and_get_token(client, "workflow-budget-blocked@example.com")
    headers = {"Authorization": f"Bearer {token}"}

    cap = client.get("/budget/status", headers=headers).json()["monthly_cap_usd"]

    from app.core.security import decode_access_token
    from app.models.user import User

    email = decode_access_token(token)
    user = db_session.query(User).filter(User.email == email).first()

    db_session.add(
        UsageRecord(
            run_id="seed-run",
            user_id=user.id,
            agent="planner",
            provider="anthropic",
            input_tokens=1_000_000,
            output_tokens=1_000_000,
            cost_usd=cap + 1.0,  # already over the cap
        )
    )
    db_session.commit()

    resp = client.post("/workflow/run", json={"task": "build a calculator"}, headers=headers)
    assert resp.status_code == 200
    body = resp.json()
    assert body["final_decision"] == "budget_exceeded"
    assert [s["agent"] for s in body["steps"]] == ["budget_guard"]