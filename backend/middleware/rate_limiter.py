"""
WBS BPKH AI - Rate Limiter Middleware
=====================================
In-memory rate limiting with bounded storage and periodic cleanup.
"""

import time
from collections import defaultdict
from typing import Dict, List, Set, Tuple

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse, Response


class RateLimiterMiddleware(BaseHTTPMiddleware):
    """
    Per-IP rate limiting middleware with memory-bounded storage.

    Args:
        app: ASGI application
        public_limit: Max requests per window for public endpoints
        auth_limit: Max requests per window for authenticated endpoints
        window_seconds: Time window in seconds
        max_keys: Maximum tracked IP:path combinations (prevents memory leak)
    """

    def __init__(
        self,
        app,
        public_limit: int = 10,
        auth_limit: int = 60,
        window_seconds: int = 60,
        max_keys: int = 10000,
    ):
        super().__init__(app)
        self.public_limit = public_limit
        self.auth_limit = auth_limit
        self.window = window_seconds
        self.max_keys = max_keys

        self._store: Dict[str, List[float]] = defaultdict(list)
        self._last_cleanup: float = 0.0

        # Exact path:method matches for public rate limiting
        self._public_exact: Dict[str, str] = {
            "/api/v1/reports": "POST",
            "/api/v1/tickets/lookup": "POST",
            "/api/v1/webhooks/whatsapp": "POST",
            "/api/v1/webhooks/email": "POST",
            "/api/v1/auth/login": "POST",
            "/api/v1/auth/forgot-password": "POST",
        }

        # Prefix-based matches for public rate limiting
        self._public_prefixes: List[Tuple[str, str]] = [
            ("/api/v1/tickets/", "POST"),
            ("/api/v1/tickets/", "GET"),
        ]

    def _is_public_limited(self, path: str, method: str) -> bool:
        """Check if request matches a rate-limited public endpoint."""
        if self._public_exact.get(path) == method:
            return True
        return any(
            path.startswith(prefix) and method == m
            for prefix, m in self._public_prefixes
        )

    def _cleanup(self, now: float) -> None:
        """Evict stale keys periodically to prevent memory leak."""
        if now - self._last_cleanup < 300:  # every 5 minutes
            return

        self._last_cleanup = now

        # Remove empty/expired keys
        stale = [
            k for k, v in self._store.items()
            if not v or now - max(v) > self.window
        ]
        for k in stale:
            del self._store[k]

        # Hard cap: drop oldest if still too many
        if len(self._store) > self.max_keys:
            sorted_keys = sorted(
                self._store.keys(),
                key=lambda k: max(self._store[k]) if self._store[k] else 0,
            )
            for k in sorted_keys[: len(self._store) - self.max_keys]:
                del self._store[k]

    async def dispatch(self, request: Request, call_next) -> Response:
        path = request.url.path
        method = request.method
        client_ip = request.client.host if request.client else "unknown"

        if self._is_public_limited(path, method):
            key = f"{client_ip}:{path}"
            now = time.time()

            # Clean old entries for this key
            self._store[key] = [
                t for t in self._store[key] if now - t < self.window
            ]

            if len(self._store[key]) >= self.public_limit:
                return JSONResponse(
                    status_code=429,
                    content={"detail": "Terlalu banyak permintaan. Coba lagi nanti."},
                )

            self._store[key].append(now)
            self._cleanup(now)

        return await call_next(request)
