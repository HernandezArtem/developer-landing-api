import re

# Casual / small-talk messages — no OpenRouter call needed
_CASUAL_PATTERNS = [
    re.compile(
        r"^(привет|здравствуй|здарова|прив|hi|hello|hey|good\s+morning|good\s+afternoon|yo)[\s,!?.\-]*$",
        re.IGNORECASE,
    ),
    re.compile(
        r"^(как\s+дела|как\s+ты|how\s+are\s+you|how'?s\s+it\s+going|what'?s\s+up|sup)[\s,!?.\-]*$",
        re.IGNORECASE,
    ),
    re.compile(
        r"^(привет|hi|hello|hey)[\s,]+(как\s+дела|как\s+ты|how\s+are\s+you)[\s,!?.\-]*$",
        re.IGNORECASE,
    ),
    re.compile(r"^(test|тест|проверка|testing)[\s,!?.\-]*$", re.IGNORECASE),
]

_OFFTOPIC_REPLIES = {
    "ru": (
        "Привет{name}! Это форма для деловых обращений по разработке — "
        "опишите задачу или проект, и я отвечу по делу."
    ),
    "en": (
        "Hi{name}! This form is for development inquiries — "
        "describe your project or task and I'll reply properly."
    ),
}


def is_casual_offtopic(comment: str) -> bool:
    """True for greetings / small talk without a real business request."""
    text = comment.strip()
    if not text or len(text) > 45:
        return False
    return any(p.match(text) for p in _CASUAL_PATTERNS)


def offtopic_reply(name: str, locale: str) -> str:
    lang = locale if locale in _OFFTOPIC_REPLIES else "ru"
    first = name.strip().split()[0] if name.strip() else ""
    suffix = f", {first}" if first else ""
    return _OFFTOPIC_REPLIES[lang].format(name=suffix)
