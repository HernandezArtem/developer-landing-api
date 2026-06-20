import time
import logging
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from app.core.request_utils import get_client_ip

logger = logging.getLogger("access")


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """Logs every HTTP request: method, path, status code, duration."""

    async def dispatch(self, request: Request, call_next):
        start = time.perf_counter()
        response = await call_next(request)
        duration_ms = round((time.perf_counter() - start) * 1000, 1)

        client_ip = get_client_ip(request)
        logger.info(
            "%s | %-6s %-40s | %s | %sms",
            client_ip,
            request.method,
            str(request.url.path),
            response.status_code,
            duration_ms,
        )
        return response
