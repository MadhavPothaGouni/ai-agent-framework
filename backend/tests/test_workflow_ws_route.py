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