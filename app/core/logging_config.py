import logging
import logging.handlers
from app.core.config import settings


def setup_logging() -> None:
    """Configure file + console logging."""
    settings.LOGS_DIR.mkdir(parents=True, exist_ok=True)

    fmt = logging.Formatter(
        fmt="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    # Rotating app log (10 MB, 5 backups)
    app_handler = logging.handlers.RotatingFileHandler(
        filename=settings.LOGS_DIR / "app.log",
        maxBytes=10 * 1024 * 1024,
        backupCount=5,
        encoding="utf-8",
    )
    app_handler.setFormatter(fmt)
    app_handler.setLevel(logging.INFO)

    # Error-only log
    err_handler = logging.handlers.RotatingFileHandler(
        filename=settings.LOGS_DIR / "error.log",
        maxBytes=5 * 1024 * 1024,
        backupCount=3,
        encoding="utf-8",
    )
    err_handler.setFormatter(fmt)
    err_handler.setLevel(logging.ERROR)

    # Console
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(fmt)
    console_handler.setLevel(logging.DEBUG if settings.DEBUG else logging.INFO)

    root = logging.getLogger()
    root.setLevel(logging.DEBUG)
    root.addHandler(app_handler)
    root.addHandler(err_handler)
    root.addHandler(console_handler)

    # Silence noisy third-party loggers
    for noisy in ("httpx", "httpcore"):
        logging.getLogger(noisy).setLevel(logging.WARNING)
