import json
import logging

# Patch httpx to ignore system SOCKS proxy (Windows registry)
import httpx._client as _httpx_client
_httpx_client.get_environment_proxies = lambda: {}

import httpx
from app.core.config import settings
from app.schemas.contact import AIAnalysis, SentimentType, CategoryType

logger = logging.getLogger(__name__)

# Fallback used when AI is unavailable or returns garbage
_FALLBACK = AIAnalysis(
    sentiment=SentimentType.neutral,
    category=CategoryType.other,
    auto_reply=(
        "Добрый день! Спасибо за ваше обращение — я его получил и свяжусь с вами "
        "в ближайшее время."
    ),
    ai_available=False,
)

_PROMPT = """Ты — помощник разработчика Артёма Hernandez.
Проанализируй сообщение и верни ТОЛЬКО валидный JSON (без markdown, без пояснений).

Поля:
- sentiment: positive | neutral | negative
- category: project_inquiry | job_offer | consultation | other
- auto_reply: готовый текст ответа пользователю (2-3 предложения на русском от лица Артёма, обратись по имени)

В auto_reply пиши только сам ответ. Не пиши инструкции, не описывай формат, не повторяй правила.

Имя отправителя: {name}
Сообщение: {comment}

Пример ответа в auto_reply:
"Привет, Иван! Спасибо за интерес к проекту — опишите задачу подробнее, и я свяжусь с вами в течение дня."
"""

_PROMPT_LEAK_MARKERS = (
    "2-3 предложения",
    "обратись к отправителю",
    "ответ от лица",
    "на русском языке",
    "валидный json",
    "без markdown",
)


def _looks_like_prompt_leak(text: str) -> bool:
    lower = text.lower()
    return any(marker in lower for marker in _PROMPT_LEAK_MARKERS)


def _personalized_fallback(name: str) -> str:
    first = name.strip().split()[0] if name.strip() else ""
    if first:
        return (
            f"Добрый день, {first}! Спасибо за обращение — я получил ваше сообщение "
            "и свяжусь с вами в ближайшее время."
        )
    return _FALLBACK.auto_reply


class AIService:
    """Wraps OpenRouter API (Mistral Nemo) for sentiment analysis, classification, and auto-reply generation."""

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

    async def analyze(self, name: str, comment: str) -> AIAnalysis:
        """Async wrapper for health checks and tests."""
        return self.analyze_sync(name, comment)

    def analyze_sync(self, name: str, comment: str) -> AIAnalysis:
        """
        Analyse a contact message via Mistral Nemo on OpenRouter.
        Returns a fallback result if AI is unavailable — service keeps running normally.
        """
        if not self._client:
            logger.warning("OpenRouter unavailable — using fallback AI analysis")
            return _FALLBACK

        prompt = _PROMPT.format(name=name, comment=comment)
        raw = ""

        try:
            response = self._client.post(
                "/chat/completions",
                json={
                    "model": settings.OPENROUTER_MODEL,
                    "messages": [{"role": "user", "content": prompt}],
                    "temperature": 0.3,
                    "max_tokens": 256,
                },
            )
            response.raise_for_status()
            payload = response.json()
            raw = payload["choices"][0]["message"]["content"].strip()

            # Strip markdown code fences if the model added them
            if raw.startswith("```"):
                parts = raw.split("```")
                raw = parts[1].lstrip("json").strip() if len(parts) > 1 else raw

            data = json.loads(raw)

            auto_reply = (data.get("auto_reply") or "").strip()
            if not auto_reply or _looks_like_prompt_leak(auto_reply):
                auto_reply = _personalized_fallback(name)

            return AIAnalysis(
                sentiment=SentimentType(data.get("sentiment", "neutral")),
                category=CategoryType(data.get("category", "other")),
                auto_reply=auto_reply,
                ai_available=True,
            )

        except json.JSONDecodeError:
            logger.error("OpenRouter returned non-JSON: %s", raw[:300])
            return _FALLBACK
        except ValueError as e:
            logger.error("OpenRouter returned invalid enum value: %s", e)
            return _FALLBACK
        except Exception as e:
            logger.error("OpenRouter API error: %s", e)
            return _FALLBACK
