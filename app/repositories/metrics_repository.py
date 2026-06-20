import json
import logging
from copy import deepcopy
from datetime import date
from typing import Any, Dict

from app.core.config import settings
from app.db.models import Metrics as MetricsModel
from app.db.session import db_session

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
    """Stores aggregated statistics in MySQL or data/metrics.json."""

    def __init__(self) -> None:
        if settings.use_mysql:
            return
        self._file = settings.METRICS_FILE
        self._ensure_file()

    def _ensure_file(self) -> None:
        if not self._file.exists():
            self._file.write_text(
                json.dumps(_DEFAULT, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )

    def get(self) -> Dict[str, Any]:
        if settings.use_mysql:
            return self._get_mysql()
        return self._load_json()

    def increment_total(self) -> None:
        if settings.use_mysql:
            self._mutate_mysql(lambda data: self._inc_total(data))
            return
        data = self._load_json()
        self._inc_total(data)
        self._save_json(data)

    def increment_successful(self, category: str = "other") -> None:
        if settings.use_mysql:
            self._mutate_mysql(lambda data: self._inc_successful(data, category))
            return
        data = self._load_json()
        self._inc_successful(data, category)
        self._save_json(data)

    def increment_error(self) -> None:
        if settings.use_mysql:
            self._mutate_mysql(lambda data: data.__setitem__("errors", data.get("errors", 0) + 1))
            return
        data = self._load_json()
        data["errors"] = data.get("errors", 0) + 1
        self._save_json(data)

    def increment_rate_limited(self) -> None:
        if settings.use_mysql:
            self._mutate_mysql(
                lambda data: data.__setitem__("rate_limited", data.get("rate_limited", 0) + 1)
            )
            return
        data = self._load_json()
        data["rate_limited"] = data.get("rate_limited", 0) + 1
        self._save_json(data)

    def _get_mysql(self) -> Dict[str, Any]:
        try:
            with db_session() as session:
                row = session.get(MetricsModel, 1)
                if row is None:
                    return deepcopy(_DEFAULT)
                return {
                    "total_requests": row.total_requests,
                    "successful": row.successful,
                    "errors": row.errors,
                    "rate_limited": row.rate_limited,
                    "by_category": dict(row.by_category or _DEFAULT["by_category"]),
                    "by_day": dict(row.by_day or {}),
                }
        except Exception as e:
            logger.error("Failed to read metrics from MySQL: %s", e)
            return deepcopy(_DEFAULT)

    def _mutate_mysql(self, mutator) -> None:
        try:
            with db_session() as session:
                row = session.get(MetricsModel, 1)
                if row is None:
                    row = MetricsModel(id=1, by_category=dict(_DEFAULT["by_category"]), by_day={})
                    session.add(row)
                    session.flush()
                data = {
                    "total_requests": row.total_requests,
                    "successful": row.successful,
                    "errors": row.errors,
                    "rate_limited": row.rate_limited,
                    "by_category": dict(row.by_category or _DEFAULT["by_category"]),
                    "by_day": dict(row.by_day or {}),
                }
                mutator(data)
                row.total_requests = data["total_requests"]
                row.successful = data["successful"]
                row.errors = data["errors"]
                row.rate_limited = data["rate_limited"]
                row.by_category = data["by_category"]
                row.by_day = data["by_day"]
        except Exception as e:
            logger.error("Failed to save metrics to MySQL: %s", e)

    @staticmethod
    def _inc_total(data: Dict[str, Any]) -> None:
        data["total_requests"] = data.get("total_requests", 0) + 1
        today = date.today().isoformat()
        data.setdefault("by_day", {})[today] = data["by_day"].get(today, 0) + 1

    @staticmethod
    def _inc_successful(data: Dict[str, Any], category: str) -> None:
        data["successful"] = data.get("successful", 0) + 1
        data.setdefault("by_category", {})
        data["by_category"][category] = data["by_category"].get(category, 0) + 1

    def _load_json(self) -> Dict[str, Any]:
        try:
            return json.loads(self._file.read_text(encoding="utf-8"))
        except Exception:
            return deepcopy(_DEFAULT)

    def _save_json(self, data: Dict[str, Any]) -> None:
        try:
            self._file.write_text(
                json.dumps(data, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
        except OSError as e:
            logger.error("Failed to save metrics: %s", e)
