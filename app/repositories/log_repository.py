import json
import logging
from datetime import datetime
from typing import Any, Dict

from sqlalchemy import delete, func, select

from app.core.config import settings
from app.db.models import Contact as ContactModel
from app.db.session import db_session

logger = logging.getLogger(__name__)


class LogRepository:
    """Stores contact submissions in MySQL or data/logs/contacts.json."""

    def __init__(self) -> None:
        if settings.use_mysql:
            return
        self._file = settings.CONTACTS_LOG_FILE
        self._ensure_file()

    def _ensure_file(self) -> None:
        if not self._file.exists():
            self._file.write_text("[]", encoding="utf-8")

    def save_contact(self, data: Dict[str, Any]) -> None:
        if settings.use_mysql:
            self._save_contact_mysql(data)
            return
        self._save_contact_json(data)

    def update_email_errors(self, request_id: str, email_errors: list[str]) -> None:
        if settings.use_mysql:
            self._update_email_errors_mysql(request_id, email_errors)
            return
        self._update_email_errors_json(request_id, email_errors)

    def _save_contact_mysql(self, data: Dict[str, Any]) -> None:
        try:
            with db_session() as session:
                session.add(
                    ContactModel(
                        request_id=data["request_id"],
                        ip=data.get("ip"),
                        name=data.get("name"),
                        phone=data.get("phone"),
                        email=data.get("email"),
                        comment_length=data.get("comment_length"),
                        sentiment=data.get("sentiment"),
                        category=data.get("category"),
                        ai_available=bool(data.get("ai_available")),
                        email_errors=data.get("email_errors") or [],
                        created_at=datetime.utcnow(),
                    )
                )
                session.flush()
                total = session.scalar(select(func.count()).select_from(ContactModel)) or 0
                if total > 10_000:
                    oldest_ids = session.scalars(
                        select(ContactModel.id)
                        .order_by(ContactModel.id.asc())
                        .limit(total - 10_000)
                    ).all()
                    if oldest_ids:
                        session.execute(
                            delete(ContactModel).where(ContactModel.id.in_(oldest_ids))
                        )
        except Exception as e:
            logger.error("Failed to write contact to MySQL: %s", e)

    def _update_email_errors_mysql(self, request_id: str, email_errors: list[str]) -> None:
        try:
            with db_session() as session:
                row = session.scalar(
                    select(ContactModel).where(ContactModel.request_id == request_id)
                )
                if row is None:
                    return
                row.email_errors = email_errors
        except Exception as e:
            logger.error("Failed to update contact in MySQL: %s", e)

    def _save_contact_json(self, data: Dict[str, Any]) -> None:
        try:
            records: list = json.loads(self._file.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            records = []

        records.append({"timestamp": datetime.utcnow().isoformat() + "Z", **data})

        if len(records) > 10_000:
            records = records[-10_000:]

        try:
            self._file.write_text(
                json.dumps(records, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
        except OSError as e:
            logger.error("Failed to write contacts log: %s", e)

    def _update_email_errors_json(self, request_id: str, email_errors: list[str]) -> None:
        try:
            records: list = json.loads(self._file.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            return

        for record in reversed(records):
            if record.get("request_id") == request_id:
                record["email_errors"] = email_errors
                break
        else:
            return

        try:
            self._file.write_text(
                json.dumps(records, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
        except OSError as e:
            logger.error("Failed to update contacts log: %s", e)
