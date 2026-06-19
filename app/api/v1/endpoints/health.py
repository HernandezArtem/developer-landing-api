import time
import asyncio
import logging
from concurrent.futures import ThreadPoolExecutor
from fastapi import APIRouter
from app.core.config import settings
from app.services.ai_service import AIService
from app.services.email_service import EmailService

router = APIRouter()
logger = logging.getLogger(__name__)

_start_time = time.time()
_executor = ThreadPoolExecutor(max_workers=1)


@router.get(
    "/health",
    summary="Проверка статуса сервиса",
    description="Проверяет доступность всех компонентов: API, AI, SMTP.",
)
async def health_check() -> dict:
    ai = AIService()
    email = EmailService()

    # Run SMTP check in thread with timeout so endpoint never hangs
    loop = asyncio.get_event_loop()
    try:
        email_ok = await asyncio.wait_for(
            loop.run_in_executor(_executor, email.check_connection),
            timeout=5.0,
        )
    except asyncio.TimeoutError:
        email_ok = False
        logger.warning("SMTP health check timed out")

    return {
        "status": "ok",
        "version": settings.APP_VERSION,
        "ai_available": ai.is_available,
        "email_available": email_ok,
        "uptime_seconds": int(time.time() - _start_time),
    }
