
import threading
from dataclasses import dataclass, field


@dataclass
class ApprovalTicket:
    event: threading.Event = field(default_factory=threading.Event)
    approved: bool | None = None


class ApprovalRegistry:
    def __init__(self) -> None:
        self._tickets: dict[str, ApprovalTicket] = {}
        self._lock = threading.Lock()

    def create(self, approval_id: str) -> ApprovalTicket:
        ticket = ApprovalTicket()
        with self._lock:
            self._tickets[approval_id] = ticket
        return ticket

    def resolve(self, approval_id: str, approved: bool) -> bool:
        """Called by whichever channel (WS message or REST call) the human
        used to respond. Returns False if the ticket doesn't exist (already
        resolved, timed out, or never created) so callers can 404/ignore.
        """
        with self._lock:
            ticket = self._tickets.get(approval_id)
        if ticket is None or ticket.event.is_set():
            return False
        ticket.approved = approved
        ticket.event.set()
        return True

    def wait(self, approval_id: str, timeout: float | None = None) -> bool | None:
        """Blocks the calling thread until resolved or `timeout` seconds
        elapse. Returns True/False for the decision, or None on timeout
        (treated as an implicit rejection by the caller).
        """
        with self._lock:
            ticket = self._tickets.get(approval_id)
        if ticket is None:
            return None
        if not ticket.event.wait(timeout):
            return None
        return ticket.approved

    def discard(self, approval_id: str) -> None:
        with self._lock:
            self._tickets.pop(approval_id, None)

    def exists(self, approval_id: str) -> bool:
        with self._lock:
            return approval_id in self._tickets


_registry = ApprovalRegistry()


def get_approval_registry() -> ApprovalRegistry:
    return _registry