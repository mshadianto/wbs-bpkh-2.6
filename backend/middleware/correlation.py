"""
WBS BPKH AI - Request Correlation Middleware
=============================================
Attaches a unique request ID to every request for log traceability.
"""

import uuid

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response
from loguru import logger


class RequestCorrelationMiddleware(BaseHTTPMiddleware):
    """
    Adds a unique X-Request-ID header to every request/response.

    If the client sends an X-Request-ID header, it is preserved.
    Otherwise a new UUID is generated.

    The request ID is also available as ``request.state.request_id``
    for use in downstream handlers and services.
    """

    HEADER = "X-Request-ID"

    async def dispatch(self, request: Request, call_next) -> Response:
        request_id = request.headers.get(self.HEADER) or uuid.uuid4().hex[:16]
        request.state.request_id = request_id

        # Bind request_id to loguru context for structured logging
        with logger.contextualize(request_id=request_id):
            response = await call_next(request)

        response.headers[self.HEADER] = request_id
        return response
