
import contextvars
from dataclasses import dataclass, field

from app.core.pricing import cost_for
from app.core.providers.base import LLMProvider
from app.core.token_counter import estimate_tokens


@dataclass
class UsageEvent:
    agent: str
    provider: str
    input_tokens: int
    output_tokens: int
    cost_usd: float


@dataclass
class CostLedger:
    events: list[UsageEvent] = field(default_factory=list)

    def record(self, agent: str, provider: str, input_tokens: int, output_tokens: int) -> UsageEvent:
        event = UsageEvent(
            agent=agent,
            provider=provider,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            cost_usd=cost_for(provider, input_tokens, output_tokens),
        )
        self.events.append(event)
        return event

    @property
    def total_cost_usd(self) -> float:
        return round(sum(e.cost_usd for e in self.events), 8)

    @property
    def total_tokens(self) -> int:
        return sum(e.input_tokens + e.output_tokens for e in self.events)


_current_ledger: "contextvars.ContextVar[CostLedger | None]" = contextvars.ContextVar(
    "_current_ledger", default=None
)
_current_agent: "contextvars.ContextVar[str]" = contextvars.ContextVar("_current_agent", default="unknown")


def start_ledger() -> CostLedger:
    """Starts (or restarts) the cost ledger for the current thread's run."""
    ledger = CostLedger()
    _current_ledger.set(ledger)
    return ledger


def get_current_ledger() -> CostLedger | None:
    return _current_ledger.get()


def set_current_agent(name: str) -> None:
    _current_agent.set(name)


class MeteredProvider(LLMProvider):
    """Wraps any LLMProvider so every .complete() call is metered into
    whatever CostLedger is active at call time. Fully transparent to
    callers: same method signature, same string return type, and even
    forwards `.name` so `provider.name == "mock"`-style checks in the
    agents keep working unmodified.
    """

    def __init__(self, inner: LLMProvider) -> None:
        self._inner = inner
        self.name = inner.name

    def complete(self, messages: list[dict[str, str]]) -> str:
        input_text = "\n".join(m.get("content", "") for m in messages)
        input_tokens = estimate_tokens(input_text)

        reply = self._inner.complete(messages)

        output_tokens = estimate_tokens(reply)

        ledger = get_current_ledger()
        if ledger is not None:
            ledger.record(_current_agent.get(), self._inner.name, input_tokens, output_tokens)

        return reply