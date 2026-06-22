import logging
from contextlib import contextmanager

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import settings
from app.db.base import Base
from app.db.models import Metrics

logger = logging.getLogger(__name__)

_engine = None
_SessionLocal = None

_DEFAULT_CATEGORIES = {
    "project_inquiry": 0,
    "job_offer": 0,
    "consultation": 0,
    "other": 0,
}


def get_engine():
    global _engine, _SessionLocal
    if not settings.use_mysql:
        return None
    if _engine is None:
        _engine = create_engine(
            settings.DATABASE_URL,
            pool_pre_ping=True,
            pool_recycle=3600,
        )
        _SessionLocal = sessionmaker(bind=_engine, autoflush=False, autocommit=False)
    return _engine


def get_session() -> Session:
    get_engine()
    if _SessionLocal is None:
        raise RuntimeError("MySQL is not configured")
    return _SessionLocal()


@contextmanager
def db_session():
    session = get_session()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def init_db() -> None:
    if not settings.use_mysql:
        return
    try:
        engine = get_engine()
        Base.metadata.create_all(bind=engine)
        _migrate_rate_limits_window_start(engine)
        with db_session() as session:
            row = session.get(Metrics, 1)
            if row is None:
                session.add(
                    Metrics(
                        id=1,
                        by_category=dict(_DEFAULT_CATEGORIES),
                        by_day={},
                    )
                )
        logger.info("MySQL tables ready")
    except Exception as e:
        logger.error("MySQL init failed — check DATABASE_URL: %s", e)


def _migrate_rate_limits_window_start(engine) -> None:
    """Ensure window_start is BIGINT unix seconds (not DATETIME/FLOAT)."""
    from sqlalchemy import text

    try:
        with engine.connect() as conn:
            conn.execute(
                text(
                    """
                    ALTER TABLE rate_limits
                    MODIFY window_start BIGINT UNSIGNED NOT NULL DEFAULT 0
                    """
                )
            )
            conn.commit()
        logger.info("rate_limits.window_start migrated to BIGINT")
    except Exception as e:
        logger.warning("rate_limits migration skipped (may already be ok): %s", e)
