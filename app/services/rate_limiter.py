import json
import logging
import time
from datetime import datetime

from sqlalchemy import text
from sqlalchemy.exc import IntegrityError, SQLAlchemyError

from app.core.config import settings
from app.core.exceptions import RateLimitExceeded
from app.db.models import RateLimit as RateLimitModel
from app.db.session import db_session

logger = logging.getLogger(__name__)

_MIN_VALID_TS = 1_000_000_000


class RateLimiter:
    """
    Rate limiter backed by MySQL or a JSON file.
    Fixed window per IP: N requests per window.
    """

    def __init__(self) -> None:
        self._file = settings.RATE_LIMITS_FILE
        if not settings.use_mysql:
            self._ensure_file()

    @property
    def _max(self) -> int:
        return max(1, settings.RATE_LIMIT_REQUESTS)

    @property
    def _window(self) -> int:
        return max(30, settings.RATE_LIMIT_WINDOW_SECONDS)

    def _ensure_file(self) -> None:
        if not self._file.exists():
            self._file.write_text("{}", encoding="utf-8")

    @staticmethod
    def _as_ts(value: object) -> int:
        if value is None:
            return 0
        if isinstance(value, datetime):
            return int(value.timestamp())
        try:
            ts = int(float(value))  # type: ignore[arg-type]
        except (TypeError, ValueError):
            return 0
        if ts > 2_000_000_000_000:
            ts //= 1000
        return ts

    @staticmethod
    def _window_is_active(window_start: int, now: int, window: int) -> bool:
        if window_start < _MIN_VALID_TS:
            return False
        if window_start > now + 120:
            return False
        return (now - window_start) < window

    def check_and_increment(self, ip: str) -> None:
        if settings.use_mysql:
            self._check_and_increment_mysql(ip)
            return
        self._ensure_file()
        self._check_and_increment_json(ip)

    def _check_and_increment_mysql(self, ip: str) -> None:
        now = int(time.time())
        window = self._window
        mx = self._max

        for attempt in range(3):
            try:
                with db_session() as session:
                    # Atomic increment when window is active and under limit.
                    updated = session.execute(
                        text(
                            """
                            UPDATE rate_limits
                            SET count = count + 1
                            WHERE ip = :ip
                              AND count < :max
                              AND window_start >= :min_ts
                              AND window_start <= :now + 120
                              AND (:now - window_start) < :window
                            """
                        ),
                        {
                            "ip": ip,
                            "max": mx,
                            "min_ts": _MIN_VALID_TS,
                            "now": now,
                            "window": window,
                        },
                    ).rowcount

                    if updated == 1:
                        row = session.get(RateLimitModel, ip)
                        logger.info(
                            "Rate limit ok: ip=%s count=%s/%d window=%ds",
                            ip, row.count if row else "?", mx, window,
                        )
                        return

                    row = session.get(RateLimitModel, ip)
                    if row is None:
                        session.add(
                            RateLimitModel(ip=ip, count=1, window_start=now)
                        )
                        logger.info(
                            "Rate limit ok: ip=%s count=1/%d window=%ds (new)",
                            ip, mx, window,
                        )
                        return

                    count = int(row.count or 0)
                    window_start = self._as_ts(row.window_start)

                    if not self._window_is_active(window_start, now, window):
                        row.count = 1
                        row.window_start = now
                        logger.info(
                            "Rate limit ok: ip=%s count=1/%d window=%ds "
                            "(new window, was count=%d ws=%s)",
                            ip, mx, window, count, window_start,
                        )
                        return

                    elapsed = now - window_start
                    retry_after = max(1, min(window - elapsed, window))
                    self._log_limited(ip, count, window_start, now, retry_after)
                    raise RateLimitExceeded(retry_after=retry_after)
            except RateLimitExceeded:
                raise
            except IntegrityError:
                logger.debug(
                    "Rate limit insert race for ip=%s, retry %d/3", ip, attempt + 1
                )
            except SQLAlchemyError as e:
                logger.error("Rate limit MySQL error for ip=%s: %s", ip, e)
                raise

        raise RuntimeError(f"rate limit could not update row for ip={ip}")

    def _apply_limit(
        self, ip: str, count: int, window_start: int, now: int
    ) -> tuple[int, int]:
        if not self._window_is_active(window_start, now, self._window):
            return 1, now
        if count >= self._max:
            elapsed = now - window_start
            retry_after = max(1, min(self._window - elapsed, self._window))
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
