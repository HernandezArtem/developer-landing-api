import json
import logging
from datetime import datetime
from typing import Any, Dict
from app.core.config import settings

logger = logging.getLogger(__name__)


class LogRepository:
    """Stores contact submissions as a JSON array in data/logs/contacts.json."""

    def __init__(self) -> None:
        self._file = settings.CONTACTS_LOG_FILE
        self._ensure_file()

    def _ensure_file(self) -> None:
        if not self._file.exists():
            self._file.write_text("[]", encoding="utf-8")

    def save_contact(self, data: Dict[str, Any]) -> None:
        try:
            records: list = json.loads(self._file.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            records = []

        records.append({"timestamp": datetime.utcnow().isoformat() + "Z", **data})

        # Rolling window — keep last 10 000 records
        if len(records) > 10_000:
            records = records[-10_000:]

        try:
            self._file.write_text(
                json.dumps(records, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
        except OSError as e:
            logger.error("Failed to write contacts log: %s", e)

    def update_email_errors(self, request_id: str, email_errors: list[str]) -> None:
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
