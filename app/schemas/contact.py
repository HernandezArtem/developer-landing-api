import re
from enum import Enum
from typing import Optional

from email_validator import validate_email, EmailNotValidError
from pydantic import BaseModel, ValidationInfo, field_validator


class SentimentType(str, Enum):
    positive = "positive"
    neutral = "neutral"
    negative = "negative"


class CategoryType(str, Enum):
    project_inquiry = "project_inquiry"
    job_offer = "job_offer"
    consultation = "consultation"
    other = "other"


class LocaleType(str, Enum):
    ru = "ru"
    en = "en"


def _lang(info: ValidationInfo) -> str:
    loc = info.data.get("locale", LocaleType.ru)
    if isinstance(loc, LocaleType):
        return loc.value
    return str(loc) if loc in ("ru", "en") else "ru"


_MSGS = {
    "ru": {
        "name_min": "Имя должно содержать минимум 2 символа",
        "name_max": "Имя не должно превышать 100 символов",
        "name_chars": "Имя может содержать только буквы, пробелы и дефис",
        "phone_invalid": "Неверный формат. Пример: +79991234567",
        "email_required": "Укажите email",
        "email_format": "Неверный формат email. Пример: ivan@example.com",
        "email_latin": "Email только латинскими буквами, цифрами и символами (a-z, 0-9, @, точка, дефис)",
        "email_invalid": "Неверный email. Проверьте адрес и домен.",
        "email_domain": "Домен email не найден или не принимает почту. Проверьте адрес.",
        "comment_min": "Напишите хотя бы 10 символов — расскажите подробнее",
        "comment_max": "Максимум 2000 символов",
    },
    "en": {
        "name_min": "Name must be at least 2 characters",
        "name_max": "Name must not exceed 100 characters",
        "name_chars": "Name may contain letters, spaces and hyphens only",
        "phone_invalid": "Invalid format. Example: +79991234567",
        "email_required": "Enter your email",
        "email_format": "Invalid email format. Example: john@example.com",
        "email_latin": "Email must use Latin letters, digits and symbols only (a-z, 0-9, @, dot, hyphen)",
        "email_invalid": "Invalid email. Check the address and domain.",
        "email_domain": "Email domain not found or does not accept mail.",
        "comment_min": "Write at least 10 characters — tell us more",
        "comment_max": "Maximum 2000 characters",
    },
}


def _m(key: str, info: ValidationInfo) -> str:
    lang = _lang(info)
    return _MSGS.get(lang, _MSGS["ru"])[key]


_ASCII_EMAIL_RE = re.compile(
    r"^[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,63}$"
)


class ContactRequest(BaseModel):
    locale: LocaleType = LocaleType.ru
    name: str
    phone: str
    email: str
    comment: str

    @field_validator("name")
    @classmethod
    def validate_name(cls, v: str, info: ValidationInfo) -> str:
        v = v.strip()
        if len(v) < 2:
            raise ValueError(_m("name_min", info))
        if len(v) > 100:
            raise ValueError(_m("name_max", info))
        if not re.match(r"^[a-zA-Zа-яА-ЯёЁ\s\-']+$", v):
            raise ValueError(_m("name_chars", info))
        return v

    @field_validator("phone")
    @classmethod
    def validate_phone(cls, v: str, info: ValidationInfo) -> str:
        cleaned = re.sub(r"[\s\-\(\)]", "", v.strip())
        if not re.match(r"^\+?[0-9]{10,15}$", cleaned):
            raise ValueError(_m("phone_invalid", info))
        return cleaned

    @field_validator("email")
    @classmethod
    def validate_email_field(cls, v: str, info: ValidationInfo) -> str:
        v = v.strip()
        if not v:
            raise ValueError(_m("email_required", info))
        if re.search(r"[^\x00-\x7F]", v):
            raise ValueError(_m("email_latin", info))
        if not _ASCII_EMAIL_RE.match(v):
            raise ValueError(_m("email_format", info))
        try:
            result = validate_email(v, check_deliverability=True, timeout=5)
            if not result.mx:
                raise ValueError(_m("email_domain", info))
            return result.normalized
        except EmailNotValidError:
            raise ValueError(_m("email_invalid", info))

    @field_validator("comment")
    @classmethod
    def validate_comment(cls, v: str, info: ValidationInfo) -> str:
        v = v.strip()
        if len(v) < 10:
            raise ValueError(_m("comment_min", info))
        if len(v) > 2000:
            raise ValueError(_m("comment_max", info))
        return v


class AIAnalysis(BaseModel):
    sentiment: SentimentType
    category: CategoryType
    auto_reply: str
    ai_available: bool = True


class ContactResponse(BaseModel):
    success: bool
    message: str
    request_id: str
    ai_analysis: Optional[AIAnalysis] = None
