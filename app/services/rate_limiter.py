import json
import logging
import time

from sqlalchemy import text
from sqlalchemy.exc import IntegrityError

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
        self._max = max(1, settings.RATE_LIMIT_REQUESTS)
        self._window = max(60, settings.RATE_LIMIT_WINDOW_SECONDS)
        self._file = settings.RATE_LIMITS_FILE
        if not settings.use_mysql:
            self._ensure_file()

    def _ensure_file(self) -> None:
        if not self._file.exists():
            self._file.write_text("{}", encoding="utf-8")

    @staticmethod
    def _as_ts(value: float | int | None) -> int:
        if value is None:
            return 0
        try:
            ts = int(float(value))
        except (TypeError, ValueError):
            return 0
        # Guard against ms timestamps or corrupt values.
        if ts > 2_000_000_000_000:
            ts //= 1000
        return ts

    def check_and_increment(self, ip: str) -> None:
        if settings.use_mysql:
            self._check_and_increment_mysql(ip)
            return

        self._ensure_file()
        self._check_and_increment_json(ip)

    def _check_and_increment_mysql(self, ip: str) -> None:
        """
        Per-IP fixed window in MySQL.
        Integer unix timestamps only — avoids FLOAT/DATETIME drift in phpMyAdmin.
        """
        now = int(time.time())
        window = int(self._window)

        for attempt in range(3):
            try:
                with db_session() as session:
                    row = session.get(RateLimitModel, ip)

                    if row is None:
                        session.add(
                            RateLimitModel(ip=ip, count=1, window_start=now)
                        )
                        logger.info(
                            "Rate limit ok: ip=%s count=1/%d window=%ds (new)",
                            ip, self._max, self._window,
                        )
                        return

                    count = int(row.count or 0)
                    window_start = self._as_ts(row.window_start)

                    # Broken row in DB — repair anchor, keep count.
                    if window_start <= 0:
                        window_start = now
                        row.window_start = window_start
                        logger.warning(
                            "Rate limit repaired window_start for ip=%s (was 0)",
                            ip,
                        )

                    elapsed = now - window_start

                    # New window only when time really passed.
                    if elapsed >= window:
                        row.count = 1
                        row.window_start = now
                        logger.info(
                            "Rate limit ok: ip=%s count=1/%d window=%ds (new window)",
                            ip, self._max, self._window,
                        )
                        return

                    # Limit reached — block first, never reset to 1 here.
                    if count >= self._max:
                        retry_after = max(1, window - elapsed)
                        self._log_limited(
                            ip, count, window_start, now, retry_after
                        )
                        raise RateLimitExceeded(retry_after=retry_after)

                    updated = session.execute(
                        text(
                            """
                            UPDATE rate_limits
                            SET count = count + 1
                            WHERE ip = :ip
                              AND window_start = :window_start
                              AND count = :count
                              AND count < :max
                            """
                        ),
                        {
                            "ip": ip,
                            "window_start": window_start,
                            "count": count,
                            "max": self._max,
                        },
                    ).rowcount

                    if updated == 1:
                        logger.info(
                            "Rate limit ok: ip=%s count=%d/%d window=%ds",
                            ip, count + 1, self._max, self._window,
                        )
                        return

                    logger.debug(
                        "Rate limit race for ip=%s count=%d, retry %d/3",
                        ip, count, attempt + 1,
                    )
            except IntegrityError:
                logger.debug("Rate limit insert race for %s, retrying", ip)

        raise RuntimeError(f"rate limit could not update row for ip={ip}")

    def _apply_limit(
        self, ip: str, count: int, window_start: int, now: int
    ) -> tuple[int, int]:
        if window_start <= 0:
            window_start = now

        elapsed = now - window_start
        if elapsed >= self._window:
            return 1, now

        if count >= self._max:
            retry_after = max(1, int(self._window - elapsed))
            self._log_limited(ip, count, window_start, now, retry_after)
            raise RateLimitExceeded(retry_after=retry_after)

        return count + 1, window_start

    def _check_and_increment_json(self, ip: str) -> None:
        data = self._load_json()
        now = int(time.time())

        record = data.get(ip, {"count": 0, "window_start": now})
        count = int(record.get("count", 0))
        window_start = self._as_ts(record.get("window_start"))
        count, window_start = self._apply_limit(ip, count, window_start, now)

        data[ip] = {"count": count, "window_start": window_start}
        self._save_json(data)

        logger.info(
            "Rate limit ok (json): ip=%s count=%d/%d window=%ds",
            ip, count, self._max, self._window,
        )

    def _log_limited(
        self, ip: str, count: int, window_start: int, now: int, retry_after: int
    ) -> None:
        logger.warning(
            "Rate limit: ip=%s count=%d/%d elapsed=%ds window=%ds retry_after=%ds",
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
            raise RateLimitExceeded() from e
