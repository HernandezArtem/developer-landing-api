import logging
import re
from fastapi import Request
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from app.core.request_utils import get_client_ip

logger = logging.getLogger(__name__)


# ── Custom exceptions ─────────────────────────────────────────

class RateLimitExceeded(Exception):
    def __init__(self, retry_after: int = 900):
        self.retry_after = retry_after
        super().__init__(f"Rate limit exceeded. Retry after {retry_after}s")


class AIServiceError(Exception):
    """Raised when AI service fails unrecoverably (fallback should handle this)."""


class EmailServiceError(Exception):
    """Raised when email sending fails."""


# ── Exception handlers ────────────────────────────────────────

_VALIDATION_MSG_PREFIXES = re.compile(
    r"^(?:Value error,\s*|value is not a valid email address:\s*)",
    re.IGNORECASE,
)


def _clean_validation_message(msg: str) -> str:
    return _VALIDATION_MSG_PREFIXES.sub("", msg).strip()


async def validation_exception_handler(
    request: Request, exc: RequestValidationError
) -> JSONResponse:
    errors = []
    for error in exc.errors():
        field = " → ".join(str(loc) for loc in error["loc"] if loc != "body")
        errors.append({"field": field, "message": _clean_validation_message(error["msg"])})

    logger.warning("Validation error on %s %s: %s", request.method, request.url.path, errors)
    return JSONResponse(
        status_code=422,
        content={
            "success": False,
            "error": "Ошибка валидации данных",
        },
    )


async def rate_limit_exception_handler(
    request: Request, exc: RateLimitExceeded
) -> JSONResponse:
    client_ip = get_client_ip(request)
    logger.warning("Rate limit exceeded for IP %s", client_ip)
    seconds = max(1, exc.retry_after)
    if seconds >= 60:
        minutes = max(1, round(seconds / 60))
        hint = f"Попробуйте через {minutes} мин."
    else:
        hint = f"Попробуйте через {seconds} сек."
    return JSONResponse(
        status_code=429,
        headers={"Retry-After": str(seconds)},
        content={
            "success": False,
            "error": f"Слишком много запросов. {hint}",
            "retry_after_seconds": seconds,
        },
    )


async def global_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    logger.error(
        "Unhandled exception on %s %s: %s",
        request.method,
        request.url.path,
        exc,
        exc_info=True,
    )
    return JSONResponse(
        status_code=500,
        content={
            "success": False,
            "error": "Внутренняя ошибка сервера. Мы уже разбираемся.",
        },
    )
