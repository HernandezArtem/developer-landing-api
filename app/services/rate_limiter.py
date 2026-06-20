import json
import logging
from datetime import datetime

from sqlalchemy import delete, select

from app.core.config import settings
from app.core.exceptions import RateLimitExceeded
from app.db.models import RateLimit as RateLimitModel
from app.db.session import db_session

logger = logging.getLogger(__name__)


class RateLimiter:
    """
    Rate limiter backed by MySQL or a JSON file.
    Tracks request counts per IP within a sliding window.
    Default: 5 requests / 15 minutes.
    """

    def __init__(self) -> None:
        self._max = settings.RATE_LIMIT_REQUESTS
        self._window = settings.RATE_LIMIT_WINDOW_SECONDS
        self._file = settings.RATE_LIMITS_FILE
        if not settings.use_mysql:
            self._ensure_file()

    def _ensure_file(self) -> None:
        if not self._file.exists():
            self._file.write_text("{}", encoding="utf-8")

    def check_and_increment(self, ip: str) -> None:
        if settings.use_mysql:
            try:
                self._check_and_increment_mysql(ip)
                return
            except RateLimitExceeded:
                raise
            except Exception as e:
                logger.warning(
                    "Rate limit MySQL unavailable — falling back to JSON: %s", e
                )
        self._ensure_file()
        self._check_and_increment_json(ip)

    def _check_and_increment_mysql(self, ip: str) -> None:
        now = datetime.utcnow().timestamp()
        try:
            with db_session() as session:
                row = session.get(RateLimitModel, ip)
                if row is None:
                    row = RateLimitModel(ip=ip, count=0, window_start=now)
                    session.add(row)
                elif now - row.window_start > self._window:
                    row.count = 0
                    row.window_start = now

                if row.count >= self._max:
                    retry_after = int(self._window - (now - row.window_start))
                    raise RateLimitExceeded(retry_after=max(retry_after, 1))

                row.count += 1
                session.execute(
                    delete(RateLimitModel).where(
                        RateLimitModel.window_start < now - self._window
                    )
                )
        except RateLimitExceeded:
            raise

    def _check_and_increment_json(self, ip: str) -> None:
        data = self._load_json()
        now = datetime.utcnow().timestamp()

        record = data.get(ip, {"count": 0, "window_start": now})

        if now - record["window_start"] > self._window:
            record = {"count": 0, "window_start": now}

        if record["count"] >= self._max:
            retry_after = int(self._window - (now - record["window_start"]))
            raise RateLimitExceeded(retry_after=max(retry_after, 1))

        record["count"] += 1
        data[ip] = record
        data = {k: v for k, v in data.items() if now - v["window_start"] <= self._window}
        self._save_json(data)

    def _load_json(self) -> dict:
        try:
            return json.loads(self._file.read_text(encoding="utf-8"))
        except Exception:
            return {}

    def _save_json(self, data: dict) -> None:
        try:
            self._file.write_text(json.dumps(data), encoding="utf-8")
        except OSError as e:
            logger.error("Failed to save rate limit data: %s", e)
