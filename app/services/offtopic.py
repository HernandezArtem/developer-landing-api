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

# Gaming / consumer help / unrelated life topics — politely decline, no dialogue
_OFF_SCOPE_PATTERNS = [
    re.compile(
        r"\b("
        r"gta|гта|grand\s*theft|"
        r"cs:?\s*go|кс\s*го|counter[\s\-]?strike|"
        r"dota|дота|lol\b|league\s+of\s+legends|"
        r"minecraft|майнкрафт|"
        r"fortnite|roblox|valorant|варрант|"
        r"wow\b|world\s+of\s+warcraft|"
        r"steam|discord\s+nitro|"
        r"рп[\s\-]?сервер|rp[\s\-]?server|samp|rage\s*mp|alt:?v|"
        r"five\s*m|fivem|"
        r"обновлен\w*\s+\w*\s*(гта|gta)|"
        r"проблем\w*\s+обновлен|"
        r"не\s+обновляется\s+(игра|гта|gta)|"
        r"как\s+установить\s+(игру|гта|gta)|"
        r"взлом\s+(игры|аккаунта)|"
        r"донатт?\b|скины\s+в\s+игре"
        r")\b",
        re.IGNORECASE,
    ),
]

# If present, message may still be a real hire / build request (e.g. "сайт для GTA RP")
_DEV_SCOPE_PATTERNS = [
    re.compile(
        r"("
        r"сайт|веб[\s\-]?прилож|приложение|лендинг|crm|erp|"
        r"разработ\w+|заказ\w*\s+(сайт|бот|прилож)|"
        r"telegram[\s\-]?бот|телеграм[\s\-]?бот|api\b|backend|frontend|"
        r"react|vue|angular|python|fastapi|django|node\.?js|"
        r"ваканси\w+|ищем\s+разработ|junior|middle|senior|"
        r"full[\s\-]?stack|фриланс|сотрудничеств|"
        r"mvp|тз\b|figma|интеграц|"
        r"нужен\s+(сайт|бот|разработчик|программист)|"
        r"хочу\s+заказать|job\s+offer|hire|developer|web\s*app|"
        r"landing\s*page|need\s+a\s+(site|website|developer|bot)"
        r")",
        re.IGNORECASE,
    ),
]

_OFF_SCOPE_REPLIES = {
    "ru": (
        "Привет{name}! Эта форма — только для проектов по разработке "
        "и предложений о работе. По такому запросу продолжать диалог не буду. "
        "Если нужен сайт, приложение, бот или хотите предложить вакансию — напишите об этом."
    ),
    "en": (
        "Hi{name}! This form is only for software development projects "
        "and job offers. I won't continue a conversation about that topic here. "
        "If you need a website, app, bot, or want to offer a role — tell me about that."
    ),
}


def is_casual_offtopic(comment: str) -> bool:
    """True for greetings / small talk without a real business request."""
    text = comment.strip()
    if not text or len(text) > 45:
        return False
    return any(p.match(text) for p in _CASUAL_PATTERNS)


def is_off_scope_topic(comment: str) -> bool:
    """True for gaming / unrelated consumer topics without a real hire/build ask."""
    text = comment.strip()
    if not text:
        return False
    if any(p.search(text) for p in _DEV_SCOPE_PATTERNS):
        return False
    return any(p.search(text) for p in _OFF_SCOPE_PATTERNS)


_NONSENSE_REPLIES = {
    "ru": (
        "Привет{name}! Не совсем понял сообщение — "
        "опишите, пожалуйста, задачу или проект по разработке, и я отвечу по делу."
    ),
    "en": (
        "Hi{name}! I didn't quite understand the message — "
        "please describe your development task or project and I'll reply properly."
    ),
}


def is_nonsense_message(comment: str) -> bool:
    """Keyboard mash / gibberish without a real request."""
    text = comment.strip()
    if len(text) < 15:
        return False
    words = re.findall(r"[a-zA-Zа-яА-ЯёЁ]{3,}", text)
    if len(words) >= 3:
        return False
    compact = re.sub(r"\s+", "", text)
    return len(compact) >= 20 and len(words) <= 1


def nonsense_reply(name: str, locale: str) -> str:
    lang = locale if locale in _NONSENSE_REPLIES else "ru"
    first = name.strip().split()[0] if name.strip() else ""
    suffix = f", {first}" if first else ""
    return _NONSENSE_REPLIES[lang].format(name=suffix)


def offtopic_reply(name: str, locale: str) -> str:
    lang = locale if locale in _OFFTOPIC_REPLIES else "ru"
    first = name.strip().split()[0] if name.strip() else ""
    suffix = f", {first}" if first else ""
    return _OFFTOPIC_REPLIES[lang].format(name=suffix)


def off_scope_reply(name: str, locale: str) -> str:
    lang = locale if locale in _OFF_SCOPE_REPLIES else "ru"
    first = name.strip().split()[0] if name.strip() else ""
    suffix = f", {first}" if first else ""
    return _OFF_SCOPE_REPLIES[lang].format(name=suffix)
