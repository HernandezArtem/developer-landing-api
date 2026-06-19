import time
import logging
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request

logger = logging.getLogger("access")


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """Logs every HTTP request: method, path, status code, duration."""

    async def dispatch(self, request: Request, call_next):
        start = time.perf_counter()
        response = await call_next(request)
        duration_ms = round((time.perf_counter() - start) * 1000, 1)

        client_ip = request.client.host if request.client else "-"
        logger.info(
            "%s | %-6s %-40s | %s | %sms",
            client_ip,
            request.method,
            str(request.url.path),
            response.status_code,
            duration_ms,
        )
        return response
