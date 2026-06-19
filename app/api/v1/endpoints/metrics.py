from fastapi import APIRouter
from app.repositories.metrics_repository import MetricsRepository

router = APIRouter()
_metrics = MetricsRepository()


@router.get(
    "/metrics",
    summary="Статистика обращений",
    description="Возвращает агрегированную статистику: тоталы, по категориям, по дням.",
)
async def get_metrics() -> dict:
    return _metrics.get()
