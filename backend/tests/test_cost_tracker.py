import threading

from app.core.cost_tracker import (
    MeteredProvider,
    get_current_ledger,
    set_current_agent,
    start_ledger,
)
from app.core.providers.base import LLMProvider


class _FakeProvider(LLMProvider):
    name = "fake"

    def __init__(self, reply: str = "a reply of some length") -> None:
        self._reply = reply

    def complete(self, messages: list[dict[str, str]]) -> str:
        return self._reply


def test_ledger_starts_empty():
    ledger = start_ledger()
    assert ledger.events == []
    assert ledger.total_cost_usd == 0.0
    assert ledger.total_tokens == 0


def test_ledger_record_accumulates_events():
    ledger = start_ledger()
    ledger.record("planner", "anthropic", input_tokens=100, output_tokens=50)
    ledger.record("coder", "anthropic", input_tokens=200, output_tokens=100)

    assert len(ledger.events) == 2
    assert ledger.total_tokens == 450
    assert ledger.total_cost_usd > 0


def test_metered_provider_forwards_name_and_reply():
    provider = MeteredProvider(_FakeProvider())
    assert provider.name == "fake"
    assert provider.complete([{"role": "user", "content": "hi"}]) == "a reply of some length"


def test_metered_provider_records_into_active_ledger():
    ledger = start_ledger()
    set_current_agent("planner")
    provider = MeteredProvider(_FakeProvider())

    provider.complete([{"role": "user", "content": "hello there"}])

    assert len(ledger.events) == 1
    event = ledger.events[0]
    assert event.agent == "planner"
    assert event.provider == "fake"
    assert event.input_tokens > 0
    assert event.output_tokens > 0


def test_metered_provider_is_a_no_op_when_no_ledger_is_active():
    # Simulates calling a metered provider outside of DevWorkflow.run() —
    # should never raise, just silently not record anything.
    import app.core.cost_tracker as cost_tracker_module

    cost_tracker_module._current_ledger.set(None)
    provider = MeteredProvider(_FakeProvider())

    reply = provider.complete([{"role": "user", "content": "hi"}])
    assert reply == "a reply of some length"
    assert get_current_ledger() is None


def test_ledgers_are_isolated_per_thread():
    """Two concurrent DevWorkflow.run() calls on separate threads must not
    see each other's usage — this is the whole reason cost_tracker uses
    contextvars instead of a module-level global."""
    results: dict[str, int] = {}

    def worker(name: str, call_count: int) -> None:
        ledger = start_ledger()
        set_current_agent(name)
        provider = MeteredProvider(_FakeProvider())
        for _ in range(call_count):
            provider.complete([{"role": "user", "content": "hi"}])
        results[name] = len(ledger.events)

    t1 = threading.Thread(target=worker, args=("thread-a", 3))
    t2 = threading.Thread(target=worker, args=("thread-b", 7))
    t1.start()
    t2.start()
    t1.join()
    t2.join()

    assert results["thread-a"] == 3
    assert results["thread-b"] == 7