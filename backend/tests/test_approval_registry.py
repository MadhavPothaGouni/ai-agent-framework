import threading
import time

from app.agents.approval_registry import ApprovalRegistry


def test_wait_blocks_until_resolved_from_another_thread():
    registry = ApprovalRegistry()
    registry.create("a1")
    results = []

    def resolver():
        time.sleep(0.05)
        registry.resolve("a1", True)

    threading.Thread(target=resolver).start()

    start = time.monotonic()
    decision = registry.wait("a1", timeout=5)
    elapsed = time.monotonic() - start

    assert decision is True
    assert elapsed < 5  # actually resolved, didn't just time out


def test_wait_times_out_and_returns_none():
    registry = ApprovalRegistry()
    registry.create("a1")

    decision = registry.wait("a1", timeout=0.05)

    assert decision is None


def test_wait_on_unknown_ticket_returns_none_immediately():
    registry = ApprovalRegistry()
    assert registry.wait("does-not-exist", timeout=1) is None


def test_resolve_unknown_ticket_returns_false():
    registry = ApprovalRegistry()
    assert registry.resolve("does-not-exist", True) is False


def test_resolve_already_resolved_ticket_returns_false():
    registry = ApprovalRegistry()
    registry.create("a1")
    assert registry.resolve("a1", True) is True
    assert registry.resolve("a1", False) is False  # can't resolve twice


def test_discard_removes_the_ticket():
    registry = ApprovalRegistry()
    registry.create("a1")
    assert registry.exists("a1") is True
    registry.discard("a1")
    assert registry.exists("a1") is False
    assert registry.wait("a1", timeout=0.05) is None


def test_resolve_false_is_a_real_rejection_not_a_falsy_no_op():
    registry = ApprovalRegistry()
    registry.create("a1")
    assert registry.resolve("a1", False) is True
    assert registry.wait("a1", timeout=1) is False