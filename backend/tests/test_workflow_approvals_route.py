def _signup_and_get_token(client, email):
    resp = client.post("/auth/signup", json={"email": email, "password": "secret123"})
    return resp.json()["access_token"]


def test_pending_approvals_empty_when_none_outstanding(client):
    token = _signup_and_get_token(client, "approvals-empty@example.com")

    resp = client.get("/workflow/approvals/pending", headers={"Authorization": f"Bearer {token}"})

    assert resp.status_code == 200
    assert resp.json() == []


def test_pending_approvals_requires_auth(client):
    resp = client.get("/workflow/approvals/pending")
    assert resp.status_code == 401


def test_decide_unknown_approval_returns_404(client):
    token = _signup_and_get_token(client, "approvals-404@example.com")

    resp = client.post(
        "/workflow/approvals/does-not-exist/decide",
        json={"approved": True},
        headers={"Authorization": f"Bearer {token}"},
    )

    assert resp.status_code == 404


def test_rest_decide_unblocks_a_websocket_paused_run(client):
    """The real point of the REST fallback: a run that's paused waiting for
    approval over the WebSocket can also be resolved by a plain REST call —
    proving the ApprovalRegistry ticket isn't tied to the socket that
    created it.
    """
    token = _signup_and_get_token(client, "approvals-rest-unblock@example.com")
    headers = {"Authorization": f"Bearer {token}"}

    with client.websocket_connect(f"/workflow/ws/run?token={token}") as ws:
        ws.send_json({"task": "build a calculator", "require_approval": True})

        approval_msg = None
        while approval_msg is None:
            msg = ws.receive_json()
            if msg["type"] == "approval_required":
                approval_msg = msg

        approval_id = approval_msg["approval_id"]

        # Resolve it over REST instead of sending an approval_decision
        # message back over the socket.
        decide_resp = client.post(
            f"/workflow/approvals/{approval_id}/decide",
            json={"approved": True},
            headers=headers,
        )
        assert decide_resp.status_code == 200
        body = decide_resp.json()
        assert body["status"] == "approved"
        assert body["resolved_live"] is True

        # The paused workflow thread should now unblock and keep streaming.
        messages = []
        while True:
            msg = ws.receive_json()
            messages.append(msg)
            if msg["type"] == "done":
                break

    step_agents = [m["agent"] for m in messages if m["type"] == "step"]
    assert "tester" in step_agents
    assert messages[-1]["final_decision"] == "approved"


def test_decide_already_resolved_approval_returns_400(client):
    token = _signup_and_get_token(client, "approvals-double-decide@example.com")
    headers = {"Authorization": f"Bearer {token}"}

    with client.websocket_connect(f"/workflow/ws/run?token={token}") as ws:
        ws.send_json({"task": "build a calculator", "require_approval": True})

        approval_msg = None
        while approval_msg is None:
            msg = ws.receive_json()
            if msg["type"] == "approval_required":
                approval_msg = msg

        approval_id = approval_msg["approval_id"]
        ws.send_json({"type": "approval_decision", "approval_id": approval_id, "approved": True})

        while True:
            msg = ws.receive_json()
            if msg["type"] == "done":
                break

    resp = client.post(
        f"/workflow/approvals/{approval_id}/decide",
        json={"approved": False},
        headers=headers,
    )
    assert resp.status_code == 400


def test_decide_someone_elses_approval_returns_404(client):
    owner_token = _signup_and_get_token(client, "approvals-owner@example.com")
    other_token = _signup_and_get_token(client, "approvals-other@example.com")

    with client.websocket_connect(f"/workflow/ws/run?token={owner_token}") as ws:
        ws.send_json({"task": "build a calculator", "require_approval": True})

        approval_msg = None
        while approval_msg is None:
            msg = ws.receive_json()
            if msg["type"] == "approval_required":
                approval_msg = msg

        approval_id = approval_msg["approval_id"]

        resp = client.post(
            f"/workflow/approvals/{approval_id}/decide",
            json={"approved": True},
            headers={"Authorization": f"Bearer {other_token}"},
        )
        assert resp.status_code == 404

        # Clean up: resolve it for real as the owner so the worker thread
        # doesn't sit blocked for the rest of the test run.
        ws.send_json({"type": "approval_decision", "approval_id": approval_id, "approved": True})
        while True:
            msg = ws.receive_json()
            if msg["type"] == "done":
                break