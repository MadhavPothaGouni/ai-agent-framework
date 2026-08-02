import pytest
from starlette.testclient import WebSocketDisconnect


def _signup_and_get_token(client, email):
    resp = client.post("/auth/signup", json={"email": email, "password": "secret123"})
    return resp.json()["access_token"]


def test_ws_run_streams_steps_then_done(client):
    token = _signup_and_get_token(client, "ws-user@example.com")

    with client.websocket_connect(f"/workflow/ws/run?token={token}") as ws:
        ws.send_json({"task": "build a calculator"})

        messages = []
        while True:
            msg = ws.receive_json()
            messages.append(msg)
            if msg["type"] == "done":
                break

    step_messages = [m for m in messages if m["type"] == "step"]
    done_message = messages[-1]

    assert [m["agent"] for m in step_messages] == [
        "planner",
        "coder",
        "tester",
        "security_auditor",
        "reviewer",
    ]
    assert all(m["success"] for m in step_messages)

    assert done_message["type"] == "done"
    assert done_message["final_decision"] == "approved"
    assert done_message["attempts"] == 1
    assert done_message["run_id"]


def test_ws_run_persists_to_run_history(client):
    token = _signup_and_get_token(client, "ws-history@example.com")

    with client.websocket_connect(f"/workflow/ws/run?token={token}") as ws:
        ws.send_json({"task": "build a widget"})
        messages = []
        while True:
            msg = ws.receive_json()
            messages.append(msg)
            if msg["type"] == "done":
                break

    run_id = messages[-1]["run_id"]

    list_resp = client.get("/workflow/runs", headers={"Authorization": f"Bearer {token}"})
    run_ids = [r["run_id"] for r in list_resp.json()]
    assert run_id in run_ids


def test_ws_run_without_token_is_rejected(client):
    with pytest.raises(WebSocketDisconnect):
        with client.websocket_connect("/workflow/ws/run") as ws:
            ws.send_json({"task": "build a calculator"})
            ws.receive_json()


def test_ws_run_with_bad_token_is_rejected(client):
    with pytest.raises(WebSocketDisconnect):
        with client.websocket_connect("/workflow/ws/run?token=not-a-real-token") as ws:
            ws.send_json({"task": "build a calculator"})
            ws.receive_json()


def test_ws_run_missing_task_returns_error(client):
    token = _signup_and_get_token(client, "ws-missing-task@example.com")

    with client.websocket_connect(f"/workflow/ws/run?token={token}") as ws:
        ws.send_json({})
        msg = ws.receive_json()
        assert msg["type"] == "error"



# Human-in-the-loop approval gate, over the WebSocket itself

def test_ws_run_approval_flow_end_to_end(client):
    token = _signup_and_get_token(client, "ws-approval@example.com")

    with client.websocket_connect(f"/workflow/ws/run?token={token}") as ws:
        ws.send_json({"task": "build a calculator", "require_approval": True})

        messages = []
        approval_msg = None
        while approval_msg is None:
            msg = ws.receive_json()
            messages.append(msg)
            if msg["type"] == "approval_required":
                approval_msg = msg

        assert approval_msg["agent"] == "coder"
        assert approval_msg["approval_id"]
        assert "def solution" in approval_msg["output"]

        ws.send_json(
            {"type": "approval_decision", "approval_id": approval_msg["approval_id"], "approved": True}
        )

        while True:
            msg = ws.receive_json()
            messages.append(msg)
            if msg["type"] == "done":
                break

    step_agents = [m["agent"] for m in messages if m["type"] == "step"]
    assert step_agents == ["planner", "coder", "human_review", "tester", "security_auditor", "reviewer"]
    assert messages[-1]["final_decision"] == "approved"


def test_ws_run_approval_flow_rejection_skips_tester(client):
    token = _signup_and_get_token(client, "ws-approval-reject@example.com")

    with client.websocket_connect(f"/workflow/ws/run?token={token}") as ws:
        ws.send_json({"task": "build a calculator", "require_approval": True})

        messages = []
        approval_msg = None
        while approval_msg is None:
            msg = ws.receive_json()
            messages.append(msg)
            if msg["type"] == "approval_required":
                approval_msg = msg

        ws.send_json(
            {"type": "approval_decision", "approval_id": approval_msg["approval_id"], "approved": False}
        )

        while True:
            msg = ws.receive_json()
            messages.append(msg)
            if msg["type"] == "done":
                break

    step_agents = [m["agent"] for m in messages if m["type"] == "step"]
    assert "tester" not in step_agents
    assert step_agents == ["planner", "coder", "human_review", "reviewer"]
    assert messages[-1]["final_decision"] == "changes_requested"


def test_ws_run_approval_creates_a_persisted_approval_request(client):
    token = _signup_and_get_token(client, "ws-approval-persist@example.com")
    headers = {"Authorization": f"Bearer {token}"}

    with client.websocket_connect(f"/workflow/ws/run?token={token}") as ws:
        ws.send_json({"task": "build a calculator", "require_approval": True})

        approval_msg = None
        while approval_msg is None:
            msg = ws.receive_json()
            if msg["type"] == "approval_required":
                approval_msg = msg

        # Before responding, the pending list should show this approval.
        pending_resp = client.get("/workflow/approvals/pending", headers=headers)
        pending_ids = [p["approval_id"] for p in pending_resp.json()]
        assert approval_msg["approval_id"] in pending_ids

        ws.send_json(
            {"type": "approval_decision", "approval_id": approval_msg["approval_id"], "approved": True}
        )

        while True:
            msg = ws.receive_json()
            if msg["type"] == "done":
                break

    # After responding, it should no longer be pending.
    pending_resp_after = client.get("/workflow/approvals/pending", headers=headers)
    pending_ids_after = [p["approval_id"] for p in pending_resp_after.json()]
    assert approval_msg["approval_id"] not in pending_ids_after

def test_ws_run_done_message_includes_cost_totals(client):
    token = _signup_and_get_token(client, "ws-cost@example.com")

    with client.websocket_connect(f"/workflow/ws/run?token={token}") as ws:
        ws.send_json({"task": "build a calculator"})
        messages = []
        while True:
            msg = ws.receive_json()
            messages.append(msg)
            if msg["type"] == "done":
                break

    done_message = messages[-1]
    assert "total_cost_usd" in done_message
    assert "total_tokens" in done_message
    assert done_message["total_cost_usd"] == 0.0  # mock provider is free
    assert done_message["total_tokens"] > 0