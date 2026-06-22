import asyncio
import uuid
import logging
from fastapi import APIRouter, BackgroundTasks, Depends, Request
from app.core.request_utils import get_client_ip
from app.core.api_key import verify_contact_api_key
from app.schemas.contact import ContactRequest, ContactResponse, AIAnalysis
from app.services.ai_service import AIService
from app.services.email_service import EmailService
from app.services.rate_limiter import RateLimiter
from app.repositories.log_repository import LogRepository
from app.repositories.metrics_repository import MetricsRepository
from app.core.exceptions import RateLimitExceeded

router = APIRouter()
logger = logging.getLogger(__name__)

# Singletons — initialised once at import time
_ai = AIService()
_email = EmailService()
_rate = RateLimiter()
_log_repo = LogRepository()
_metrics = MetricsRepository()


def _send_emails_and_update_log(
    data: ContactRequest,
    ai_result: AIAnalysis,
    request_id: str,
    client_ip: str,
) -> None:
    """Background task: send emails without blocking the HTTP response."""
    email_errors: list[str] = []

    try:
        _email.send_notifications(data, ai_result, request_id)
    except Exception as e:
        logger.error("[%s] Email delivery failed: %s", request_id, e)
        email_errors.append("delivery")

    if email_errors:
        _log_repo.update_email_errors(request_id, email_errors)
        logger.warning("[%s] Email errors: %s", request_id, email_errors)
    else:
        logger.info("[%s] Emails sent in background", request_id)


@router.post(
    "/contact",
    response_model=ContactResponse,
    summary="Отправить обращение",
    description=(
        "Принимает форму обратной связи. "
        "Валидирует данные → анализирует через AI → отправляет email уведомления → логирует."
    ),
    responses={
        200: {"description": "Обращение успешно принято"},
        401: {"description": "Неверный или отсутствующий API-ключ"},
        422: {"description": "Ошибка валидации данных"},
        429: {"description": "Превышен rate limit (5 запросов / 15 мин с одного IP)"},
        500: {"description": "Внутренняя ошибка сервера"},
    },
)
async def submit_contact(
    request: Request,
    data: ContactRequest,
    background_tasks: BackgroundTasks,
    _: None = Depends(verify_contact_api_key),
) -> ContactResponse:
    client_ip = get_client_ip(request)

    # ── 1. Rate limiting ──────────────────────────────────────
    try:
        _rate.check_and_increment(client_ip)
    except RateLimitExceeded:
        _metrics.increment_rate_limited()
        raise

    request_id = str(uuid.uuid4())
    _metrics.increment_total()
    logger.info("[%s] New contact from %s (%s)", request_id, data.email, client_ip)

    # ── 2. AI analysis (graceful fallback built-in) ───────────
    ai_result = await asyncio.to_thread(
        _ai.analyze_sync, data.name, data.comment, data.locale.value
    )
    logger.info(
        "[%s] AI: sentiment=%s category=%s available=%s",
        request_id, ai_result.sentiment, ai_result.category, ai_result.ai_available,
    )

    # ── 3. Log + respond immediately; emails go to background ─
    _log_repo.save_contact(
        {
            "request_id": request_id,
            "ip": client_ip,
            "name": data.name,
            "phone": data.phone,
            "email": data.email,
            "comment": data.comment,
            "comment_length": len(data.comment),
            "sentiment": ai_result.sentiment,
            "category": ai_result.category,
            "ai_available": ai_result.ai_available,
            "email_errors": [],
        }
    )
    _metrics.increment_successful(ai_result.category)

    background_tasks.add_task(
        _send_emails_and_update_log,
        data,
        ai_result,
        request_id,
        client_ip,
    )

    logger.info("[%s] Contact accepted, emails queued", request_id)

    _SUCCESS_MSG = {
        "ru": "Обращение принято! Отвечу в ближайшее время.",
        "en": "Message received! I'll get back to you soon.",
    }

    return ContactResponse(
        success=True,
        message=_SUCCESS_MSG.get(data.locale.value, _SUCCESS_MSG["ru"]),
        request_id=request_id,
        ai_analysis=ai_result,
    )
