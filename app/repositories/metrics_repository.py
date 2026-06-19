import json
import logging
from datetime import date
from typing import Any, Dict
from app.core.config import settings

logger = logging.getLogger(__name__)

_DEFAULT: Dict[str, Any] = {
    "total_requests": 0,
    "successful": 0,
    "errors": 0,
    "rate_limited": 0,
    "by_category": {
        "project_inquiry": 0,
        "job_offer": 0,
        "consultation": 0,
        "other": 0,
    },
    "by_day": {},
}


class MetricsRepository:
    """Stores aggregated statistics in data/metrics.json."""

    def __init__(self) -> None:
        self._file = settings.METRICS_FILE
        self._ensure_file()

    def _ensure_file(self) -> None:
        if not self._file.exists():
            self._file.write_text(
                json.dumps(_DEFAULT, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )

    def _load(self) -> Dict[str, Any]:
        try:
            return json.loads(self._file.read_text(encoding="utf-8"))
        except Exception:
            return dict(_DEFAULT)

    def _save(self, data: Dict[str, Any]) -> None:
        try:
            self._file.write_text(
                json.dumps(data, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
        except OSError as e:
            logger.error("Failed to save metrics: %s", e)

    def get(self) -> Dict[str, Any]:
        return self._load()

    def increment_total(self) -> None:
        data = self._load()
        data["total_requests"] = data.get("total_requests", 0) + 1
        today = date.today().isoformat()
        data.setdefault("by_day", {})[today] = data["by_day"].get(today, 0) + 1
        self._save(data)

    def increment_successful(self, category: str = "other") -> None:
        data = self._load()
        data["successful"] = data.get("successful", 0) + 1
        data.setdefault("by_category", {})
        data["by_category"][category] = data["by_category"].get(category, 0) + 1
        self._save(data)

    def increment_error(self) -> None:
        data = self._load()
        data["errors"] = data.get("errors", 0) + 1
        self._save(data)

    def increment_rate_limited(self) -> None:
        data = self._load()
        data["rate_limited"] = data.get("rate_limited", 0) + 1
        self._save(data)
