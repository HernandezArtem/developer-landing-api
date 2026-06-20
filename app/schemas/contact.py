import re
from enum import Enum
from typing import Optional
from email_validator import validate_email, EmailNotValidError
from pydantic import BaseModel, EmailStr, field_validator


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


class ContactRequest(BaseModel):
    name: str
    phone: str
    email: EmailStr
    comment: str
    locale: LocaleType = LocaleType.ru

    @field_validator("name")
    @classmethod
    def validate_name(cls, v: str) -> str:
        v = v.strip()
        if len(v) < 2:
            raise ValueError("Имя должно содержать минимум 2 символа")
        if len(v) > 100:
            raise ValueError("Имя не должно превышать 100 символов")
        if not re.match(r"^[a-zA-Zа-яА-ЯёЁ\s\-']+$", v):
            raise ValueError("Имя может содержать только буквы, пробелы и дефис")
        return v

    @field_validator("phone")
    @classmethod
    def validate_phone(cls, v: str) -> str:
        # Strip formatting chars
        cleaned = re.sub(r"[\s\-\(\)]", "", v.strip())
        if not re.match(r"^\+?[0-9]{10,15}$", cleaned):
            raise ValueError("Неверный формат. Пример: +79991234567")
        return cleaned

    @field_validator("email")
    @classmethod
    def validate_email_domain(cls, v: str) -> str:
        """Проверка домена: MX/A-записи через DNS (без SMTP-проверки ящика)."""
        try:
            result = validate_email(v, check_deliverability=True, timeout=5)
            # email-validator пропускает домен при DNS timeout / NoNameservers —
            # без MX/A считаем адрес невалидным.
            if not result.mx:
                raise ValueError(
                    "Домен email не найден или не принимает почту. Проверьте адрес."
                )
            return result.normalized
        except EmailNotValidError:
            raise ValueError(
                "Домен email не найден или не принимает почту. Проверьте адрес."
            )

    @field_validator("comment")
    @classmethod
    def validate_comment(cls, v: str) -> str:
        v = v.strip()
        if len(v) < 10:
            raise ValueError("Напишите хотя бы 10 символов — расскажите подробнее")
        if len(v) > 2000:
            raise ValueError("Максимум 2000 символов")
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
