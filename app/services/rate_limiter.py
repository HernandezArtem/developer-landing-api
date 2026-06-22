import json
import logging
import time

from sqlalchemy import select

from app.core.config import settings
from app.core.exceptions import RateLimitExceeded
from app.db.models import RateLimit as RateLimitModel
from app.db.session import db_session

logger = logging.getLogger(__name__)


class RateLimiter:
    """
    Rate limiter backed by MySQL or a JSON file.
    Fixed window per IP: N requests per window (default 5 / 15 min).
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

    def _window_expired(self, now: float, window_start: float) -> bool:
        elapsed = now - window_start
        # elapsed < 0 — сбой часов или битые данные; сбрасываем окно
        return elapsed < 0 or elapsed >= self._window

    def _reset_record(self, now: float) -> tuple[int, float]:
        return 0, now

    def check_and_increment(self, ip: str) -> None:
        if settings.use_mysql:
            try:
                self._check_and_increment_mysql(ip)
                return
            except RateLimitExceeded:
                raise
            except Exception as e:
                # На prod не читаем устаревший JSON — иначе лимит «залипает» навсегда
                logger.error("Rate limit MySQL failed for %s — request allowed: %s", ip, e)
                return

        self._ensure_file()
        self._check_and_increment_json(ip)

    def _check_and_increment_mysql(self, ip: str) -> None:
        now = time.time()
        with db_session() as session:
            row = session.execute(
                select(RateLimitModel)
                .where(RateLimitModel.ip == ip)
                .with_for_update()
            ).scalar_one_or_none()

            if row is None:
                count, window_start = self._reset_record(now)
                row = RateLimitModel(ip=ip, count=count, window_start=window_start)
                session.add(row)
            else:
                count, window_start = row.count, row.window_start
                if self._window_expired(now, window_start):
                    count, window_start = self._reset_record(now)
                    row.count = count
                    row.window_start = window_start

            if count >= self._max:
                elapsed = now - window_start
                retry_after = int(self._window - elapsed)
                if retry_after <= 0:
                    count, window_start = self._reset_record(now)
                    row.count = count
                    row.window_start = window_start
                else:
                    self._log_limited(ip, count, window_start, now, retry_after)
                    raise RateLimitExceeded(retry_after=retry_after)

            row.count = count + 1

    def _check_and_increment_json(self, ip: str) -> None:
        data = self._load_json()
        now = time.time()

        record = data.get(ip, {"count": 0, "window_start": now})
        count, window_start = record["count"], record["window_start"]

        if self._window_expired(now, window_start):
            count, window_start = self._reset_record(now)

        if count >= self._max:
            elapsed = now - window_start
            retry_after = int(self._window - elapsed)
            if retry_after <= 0:
                count, window_start = self._reset_record(now)
            else:
                self._log_limited(ip, count, window_start, now, retry_after)
                raise RateLimitExceeded(retry_after=retry_after)

        count += 1
        data[ip] = {"count": count, "window_start": window_start}
        data = {
            k: v for k, v in data.items()
            if now - v["window_start"] < self._window
        }
        self._save_json(data)

    def _log_limited(
        self, ip: str, count: int, window_start: float, now: float, retry_after: int
    ) -> None:
        logger.warning(
            "Rate limit: ip=%s count=%d/%d elapsed=%.0fs window=%ds retry_after=%ds",
            ip, count, self._max, now - window_start, self._window, retry_after,
        )

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
