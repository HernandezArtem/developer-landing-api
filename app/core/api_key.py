import secrets

from fastapi import Header

from app.core.config import settings
from app.core.exceptions import InvalidAPIKey


def verify_contact_api_key(x_api_key: str | None = Header(None, alias="X-API-Key")) -> None:
    """Require X-API-Key when CONTACT_API_KEY is set in .env."""
    expected = settings.CONTACT_API_KEY.strip()
    if not expected:
        return
    if not x_api_key or not secrets.compare_digest(x_api_key, expected):
        raise InvalidAPIKey()
