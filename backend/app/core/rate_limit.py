
import threading
import time
from collections import defaultdict, deque
from collections.abc import Callable

from fastapi import Depends, HTTPException, Request, status

from app.core.security import get_current_user
from app.models.user import User

_all_limiters: list["RateLimiter"] = []


class RateLimiter:
    def __init__(self, max_requests: int, window_seconds: float) -> None:
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self._hits: dict[str, deque[float]] = defaultdict(deque)
        self._lock = threading.Lock()
        _all_limiters.append(self)

    def check(self, key: str) -> bool:
        now = time.monotonic()
        with self._lock:
            hits = self._hits[key]
            while hits and now - hits[0] > self.window_seconds:
                hits.popleft()
            if len(hits) >= self.max_requests:
                return False
            hits.append(now)
            return True

    def reset(self) -> None:
        with self._lock:
            self._hits.clear()


def reset_all_limiters() -> None:
    """Test-only helper: clears state on every limiter created so far."""
    for limiter in _all_limiters:
        limiter.reset()


def client_ip_key(request: Request) -> str:
    client = request.client.host if request.client else "unknown"
    return f"{request.url.path}:{client}"


def ip_rate_limited(max_requests: int, window_seconds: float) -> Callable:
    """Dependency factory: limits by client IP + path. Use for unauthenticated
    routes (signup/login) where there's no user id yet to key on.
    """
    limiter = RateLimiter(max_requests, window_seconds)

    def dependency(request: Request) -> None:
        if not limiter.check(client_ip_key(request)):
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail=f"Too many requests. Limit is {max_requests} per {int(window_seconds)}s.",
            )

    return dependency


def user_rate_limited(max_requests: int, window_seconds: float) -> Callable:
    """Dependency factory: limits by authenticated user id. Also performs the
    auth check itself (wraps get_current_user), so routes can depend on this
    alone instead of Depends(get_current_user) and still get `current_user`.
    """
    limiter = RateLimiter(max_requests, window_seconds)

    def dependency(current_user: User = Depends(get_current_user)) -> User:
        if not limiter.check(f"user:{current_user.id}"):
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail=f"Too many requests. Limit is {max_requests} per {int(window_seconds)}s.",
            )
        return current_user

    return dependency