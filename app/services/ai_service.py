import json
import logging
import re

# Patch httpx to ignore system SOCKS proxy (Windows registry)
import httpx._client as _httpx_client
_httpx_client.get_environment_proxies = lambda: {}

import httpx
from app.core.config import settings
from app.schemas.contact import AIAnalysis, SentimentType, CategoryType
from app.services.offtopic import is_casual_offtopic, offtopic_reply

logger = logging.getLogger(__name__)

_FALLBACK_RU = (
    "Добрый день! Спасибо за ваше обращение — я его получил и свяжусь с вами "
    "в ближайшее время."
)
_FALLBACK_EN = (
    "Hello! Thank you for your message — I've received it and will get back to you soon."
)

_PROMPT = """Ты — помощник backend-разработчика Артёма Hernandez.
Проанализируй сообщение и верни ТОЛЬКО валидный JSON (без markdown).

Поля:
- sentiment: positive | neutral | negative
- category: project_inquiry | job_offer | consultation | other
- auto_reply: готовый ответ пользователю (2–3 предложения от лица Артёма, обратись по имени)

Язык auto_reply: ТОЛЬКО {language}. Не смешивай языки.

Правила для auto_reply:
1. Если в сообщении УЖЕ есть детали (сфера, стек, сроки, бюджет, интеграции) — ОБЯЗАТЕЛЬНО упомяни 1–2 конкретные детали из текста. Покажи, что сообщение прочитано.
2. НЕ пиши «расскажите подробнее», «tell me more», «поделитесь деталями» — если человек уже описал задачу.
3. Если сообщение короткое и без сути — вежливо попроси описать задачу.
4. Оффтоп (просто «привет») — мягко верни к теме разработки.
5. Тон: профессионально, по-человечески, без канцелярита.

Плохой пример (слишком общий, детали проигнорированы):
«Привет, Иван! Спасибо за интерес. Расскажите больше о проекте.»

Хороший пример (есть отсылка к деталям):
«Привет, Дмитрий! Система для сети автосервисов с записью и интеграцией с 1С — понятная задача. MVP к ноябрю звучит реально — давайте созвонимся на этой неделе, посмотрю ТЗ и Figma.»

В auto_reply — только текст ответа, без пояснений.

Имя: {name}
Сообщение: {comment}
"""

_RETRY_PROMPT = """Пользователь уже отправил РАЗВЁРНУТОЕ сообщение. Верни ТОЛЬКО JSON:
{{"auto_reply": "..."}}

auto_reply на языке: {language}
Имя: {name}

Обязательно:
- Упомяни 1–2 КОНКРЕТНЫЕ детали из сообщения (отрасль, технологии, срок, интеграция, масштаб)
- НЕ проси «рассказать подробнее» / «tell me more» — детали уже есть
- 2–3 предложения от лица Артёма

Сообщение:
{comment}
"""

_PROMPT_LEAK_MARKERS = (
    "2-3 sentences",
    "2–3 предложения",
    "2-3 предложения",
    "обратись к отправителю",
    "ответ от лица",
    "from artem's voice",
    "valid json",
    "валидный json",
    "без markdown",
    "language rules",
    "content rules",
    "плохой пример",
    "хороший пример",
    "правила для auto_reply",
)

_GENERIC_REPLY_MARKERS = (
    "расскажите немного больше",
    "расскажите подробнее",
    "расскажите больше о",
    "расскажите о вашем проекте",
    "поделитесь деталями",
    "опишите задачу подробнее",
    "tell me more",
    "share a few more details",
    "share more details",
    "tell me about your project",
    "could you share more",
    "спасибо за интерес к моим услугам",
    "спасибо за интерес к моему",
    "thanks for your interest in my services",
    "thanks for reaching out about the project — share",
)

def _looks_like_prompt_leak(text: str) -> bool:
    lower = text.lower()
    return any(marker in lower for marker in _PROMPT_LEAK_MARKERS)


def _looks_like_generic_reply(text: str) -> bool:
    lower = text.lower()
    return any(marker in lower for marker in _GENERIC_REPLY_MARKERS)


def _is_detailed_message(comment: str) -> bool:
    text = comment.strip()
    if len(text) >= 100:
        return True
    return bool(re.search(r"[.!?…]\s", text)) or text.count("\n") >= 2


def _language_label(lang: str) -> str:
    return "English" if lang == "en" else "Russian"


def detect_reply_language(comment: str, site_locale: str = "ru") -> str:
    """Pick reply language from message text; fall back to site locale."""
    cyr = len(re.findall(r"[а-яА-ЯёЁ]", comment))
    lat = len(re.findall(r"[a-zA-Z]", comment))
    if lat > cyr and lat >= 3:
        return "en"
    if cyr > lat and cyr >= 3:
        return "ru"
    return site_locale if site_locale in ("ru", "en") else "ru"


def _reply_matches_language(text: str, lang: str) -> bool:
    cyr = len(re.findall(r"[а-яА-ЯёЁ]", text))
    lat = len(re.findall(r"[a-zA-Z]", text))
    if lang == "en":
        return lat > 0 and lat >= cyr
    return cyr > 0 and cyr >= lat


def _personalized_fallback(name: str, reply_lang: str) -> str:
    first = name.strip().split()[0] if name.strip() else ""
    if reply_lang == "en":
        if first:
            return (
                f"Hello, {first}! Thank you for your message — I've received it "
                "and will get back to you soon."
            )
        return _FALLBACK_EN
    if first:
        return (
            f"Добрый день, {first}! Спасибо за обращение — я получил ваше сообщение "
            "и свяжусь с вами в ближайшее время."
        )
    return _FALLBACK_RU


def _fallback_analysis(name: str, reply_lang: str) -> AIAnalysis:
    return AIAnalysis(
        sentiment=SentimentType.neutral,
        category=CategoryType.other,
        auto_reply=_personalized_fallback(name, reply_lang),
        ai_available=False,
    )


class AIService:
    """OpenRouter (Mistral Nemo): sentiment, classification, auto-reply."""

    def __init__(self) -> None:
        self._client: httpx.Client | None = None
        if settings.OPENROUTER_API_KEY:
            try:
                self._client = httpx.Client(
                    base_url=settings.OPENROUTER_BASE_URL,
                    headers={
                        "Authorization": f"Bearer {settings.OPENROUTER_API_KEY}",
                        "Content-Type": "application/json",
                    },
                    timeout=settings.AI_TIMEOUT,
                    follow_redirects=True,
                )
                logger.info(
                    "OpenRouter AI client initialized (model: %s)",
                    settings.OPENROUTER_MODEL,
                )
            except Exception as e:
                logger.error("Failed to initialize OpenRouter client: %s", e)

    @property
    def is_available(self) -> bool:
        return self._client is not None

    def _call_openrouter(self, prompt: str) -> str:
        response = self._client.post(
            "/chat/completions",
            json={
                "model": settings.OPENROUTER_MODEL,
                "messages": [{"role": "user", "content": prompt}],
                "temperature": 0.35,
                "max_tokens": 300,
            },
        )
        response.raise_for_status()
        return response.json()["choices"][0]["message"]["content"].strip()

    def _parse_json_response(self, raw: str) -> dict:
        text = raw.strip()
        if text.startswith("```"):
            parts = text.split("```")
            text = parts[1].lstrip("json").strip() if len(parts) > 1 else text
        if not text.startswith("{"):
            start = text.find("{")
            end = text.rfind("}")
            if start >= 0 and end > start:
                text = text[start : end + 1]
        return json.loads(text)

    def _parse_auto_reply(self, raw: str) -> str:
        return (self._parse_json_response(raw).get("auto_reply") or "").strip()

    def _refine_auto_reply(
        self, name: str, comment: str, reply_lang: str, auto_reply: str
    ) -> str:
        if not (_is_detailed_message(comment) and _looks_like_generic_reply(auto_reply)):
            return auto_reply
        logger.info("Generic AI reply on detailed message — retrying with context prompt")
        try:
            raw = self._call_openrouter(
                _RETRY_PROMPT.format(
                    language=_language_label(reply_lang),
                    name=name,
                    comment=comment,
                )
            )
            refined = self._parse_auto_reply(raw)
            if (
                refined
                and not _looks_like_prompt_leak(refined)
                and _reply_matches_language(refined, reply_lang)
                and not _looks_like_generic_reply(refined)
            ):
                return refined
        except Exception as e:
            logger.warning("Context retry failed: %s", e)
        return auto_reply

    async def analyze(self, name: str, comment: str, locale: str = "ru") -> AIAnalysis:
        return self.analyze_sync(name, comment, locale)

    def analyze_sync(self, name: str, comment: str, locale: str = "ru") -> AIAnalysis:
        site_lang = locale if locale in ("ru", "en") else "ru"
        reply_lang = detect_reply_language(comment, site_lang)

        if is_casual_offtopic(comment):
            logger.info(
                "Casual off-topic message — template reply (reply_lang=%s)", reply_lang
            )
            return AIAnalysis(
                sentiment=SentimentType.neutral,
                category=CategoryType.other,
                auto_reply=offtopic_reply(name, reply_lang),
                ai_available=True,
            )

        if not self._client:
            logger.warning("OpenRouter unavailable — using fallback AI analysis")
            return _fallback_analysis(name, reply_lang)

        raw = ""

        try:
            raw = self._call_openrouter(
                _PROMPT.format(
                    language=_language_label(reply_lang),
                    name=name,
                    comment=comment,
                )
            )

            data = self._parse_json_response(raw)
            auto_reply = (data.get("auto_reply") or "").strip()
            if not auto_reply or _looks_like_prompt_leak(auto_reply):
                auto_reply = _personalized_fallback(name, reply_lang)
            elif not _reply_matches_language(auto_reply, reply_lang):
                logger.warning(
                    "AI reply language mismatch (expected %s) — using fallback",
                    reply_lang,
                )
                auto_reply = _personalized_fallback(name, reply_lang)
            else:
                auto_reply = self._refine_auto_reply(
                    name, comment, reply_lang, auto_reply
                )

            return AIAnalysis(
                sentiment=SentimentType(data.get("sentiment", "neutral")),
                category=CategoryType(data.get("category", "other")),
                auto_reply=auto_reply,
                ai_available=True,
            )

        except json.JSONDecodeError:
            logger.error("OpenRouter returned non-JSON: %s", raw[:300])
            return _fallback_analysis(name, reply_lang)
        except ValueError as e:
            logger.error("OpenRouter returned invalid enum value: %s", e)
            return _fallback_analysis(name, reply_lang)
        except Exception as e:
            logger.error("OpenRouter API error: %s", e)
            return _fallback_analysis(name, reply_lang)
