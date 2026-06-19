import json
import logging
from datetime import datetime
from typing import Any, Dict
from app.core.config import settings
from app.core.exceptions import RateLimitExceeded

logger = logging.getLogger(__name__)


class RateLimiter:
    """
    File-based rate limiter.
    Tracks request counts per IP within a sliding window.
    Default: 5 requests / 15 minutes.
    """

    def __init__(self) -> None:
        self._file = settings.RATE_LIMITS_FILE
        self._max = settings.RATE_LIMIT_REQUESTS
        self._window = settings.RATE_LIMIT_WINDOW_SECONDS
        self._ensure_file()

    def _ensure_file(self) -> None:
        if not self._file.exists():
            self._file.write_text("{}", encoding="utf-8")

    def _load(self) -> Dict[str, Any]:
        try:
            return json.loads(self._file.read_text(encoding="utf-8"))
        except Exception:
            return {}

    def _save(self, data: Dict[str, Any]) -> None:
        try:
            self._file.write_text(json.dumps(data), encoding="utf-8")
        except OSError as e:
            logger.error("Failed to save rate limit data: %s", e)

    def check_and_increment(self, ip: str) -> None:
        """
        Increments the counter for ``ip``.
        Raises :class:`RateLimitExceeded` if the limit is reached.
        """
        data = self._load()
        now = datetime.utcnow().timestamp()

        record = data.get(ip, {"count": 0, "window_start": now})

        # Reset window if it has expired
        if now - record["window_start"] > self._window:
            record = {"count": 0, "window_start": now}

        if record["count"] >= self._max:
            retry_after = int(self._window - (now - record["window_start"]))
            raise RateLimitExceeded(retry_after=max(retry_after, 1))

        record["count"] += 1
        data[ip] = record

        # Purge stale entries to keep the file small
        data = {k: v for k, v in data.items() if now - v["window_start"] <= self._window}

        self._save(data)
