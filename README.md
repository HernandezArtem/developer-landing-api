# Developer Landing API

Backend-сервис и одностраничный лендинг портфолио разработчика.

**Production:** http://62.217.179.202  

REST API с AI-анализом (Mistral Nemo через OpenRouter), email-уведомлениями (mail.ru), rate limiting и двойным хранением данных (MySQL на сервере / JSON локально). Фронтенд — RU/EN с переключателем языка.

## Для проверки (без установки)

Проект уже развёрнут на сервере — **клонировать репозиторий и поднимать локально не нужно**.

| Что | URL |
|---|---|
| Лендинг | http://62.217.179.202 |
| Swagger (OpenAPI) | http://62.217.179.202/docs |

Postman: импортируйте `postman/Developer-Landing-API.postman_collection.json` — переменная `base_url` уже указывает на prod.

`http://localhost:8000` — только для локальной разработки (см. раздел ниже).

---

## Стэк

| Слой | Технология |
|---|---|
| Backend | Python 3.11, FastAPI, Pydantic v2 |
| БД (prod) | MySQL (Beget Cloud DB), SQLAlchemy |
| Хранение (local) | JSON-файлы в `data/` |
| AI | OpenRouter API (Mistral Nemo) |
| Email | mail.ru SMTP over SSL |
| Frontend | HTML + Vanilla CSS + JavaScript + i18n |
| Деплой | Beget VPS, nginx + gunicorn, GitHub Actions |

---

## Локальный запуск

Инструкция ниже — если вы клонируете репозиторий и запускаете проект у себя на машине. Для проверки готового проекта используйте prod-ссылки выше.

### 1. Клонировать проект

```bash
git clone https://github.com/HernandezArtem/developer-landing-api.git
cd developer-landing-api
```

### 2. Виртуальное окружение и зависимости

```bash
python -m venv venv

# Windows
venv\Scripts\activate

# Linux / macOS
source venv/bin/activate

pip install -r requirements.txt
```

### 3. Переменные окружения

```bash
cp .env.example .env
# Отредактировать .env — вставить реальные ключи
```

| Переменная | Описание |
|---|---|
| `SMTP_USER`, `SMTP_PASSWORD`, `OWNER_EMAIL` | Почта mail.ru |
| `OPENROUTER_API_KEY` | Ключ OpenRouter (openrouter.ai) |
| `OPENROUTER_MODEL` | По умолчанию `mistralai/mistral-nemo` |
| `DATABASE_URL` | **Локально оставить пустым** — данные в `data/*.json`. На VPS — строка MySQL (спецсимволы в пароле URL-кодируйте, `&` → `%26`) |
| `RATE_LIMIT_REQUESTS` / `RATE_LIMIT_WINDOW_SECONDS` | Лимит запросов с IP (по умолчанию 5 / 15 мин) |

### 4. Запуск локально

```bash
python -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

- Лендинг: http://localhost:8000
- Swagger: http://localhost:8000/docs

### 5. Postman

Импортируйте `postman/Developer-Landing-API.postman_collection.json`.

| Сценарий | `base_url` |
|---|---|
| Проверка на сервере (по умолчанию в коллекции) | `http://62.217.179.202` |
| Локальный запуск | `http://localhost:8000` |

---

## Архитектура

```
HTTP Request
    ↓
Endpoints (Controllers)     app/api/v1/endpoints/
    ↓
Services (бизнес-логика)    app/services/
    ↓
Repositories / DB             app/repositories/  +  app/db/
    ↓
Хранение                    MySQL (prod)  |  data/*.json (local)
```

### Почему FastAPI / OpenRouter / dual storage

- **FastAPI** — async из коробки, автогенерация OpenAPI/Swagger, Pydantic v2 для валидации на границе API; типизация снижает количество runtime-ошибок.
- **OpenRouter** — единый HTTP API к разным LLM без привязки к одному провайдеру; модель `mistralai/mistral-nemo` — быстрая и дешёвая для классификации + короткого автоответа.
- **Dual storage (MySQL + JSON)** — локально разработка без БД (`DATABASE_URL` пустой → `data/*.json`); на VPS тот же код пишет в MySQL Beget Cloud DB. Переключение только через `.env`.
- **BackgroundTasks для SMTP** — AI ~5–8 с, SMTP ~10–15 с; письма уходят после HTTP 200, пользователь не ждёт почтовый сервер.
- **Repository-слой** — `LogRepository` и `MetricsRepository` скрывают детали хранения; endpoint не знает, JSON это или MySQL.
- **Graceful degradation** — при недоступности OpenRouter или SMTP сервис отвечает 200 с fallback-текстом, ошибки пишутся в лог.
- **StaticFiles + API в одном процессе** — один gunicorn/uvicorn на VPS: лендинг на `/`, API на `/api/*`.

### Паттерны проектирования

| Паттерн | Где | Зачем |
|---|---|---|
| **Layered Architecture** | `endpoints → services → repositories` | Разделение HTTP, бизнес-логики и персистентности |
| **Repository** | `LogRepository`, `MetricsRepository`, `RateLimiter` | Единый интерфейс записи/чтения; backend — MySQL или JSON |
| **BackgroundTasks** | `contact.py` → `_send_emails_and_update_log` | Неблокирующая отправка email после ответа клиенту |
| **Singleton (module-level)** | `_ai`, `_email`, `_rate` в `contact.py` | Один httpx-клиент и SMTP-сессия на процесс |
| **Strategy (implicit)** | `settings.use_mysql` | Выбор стратегии хранения без if/else в endpoints |

### Цикл обработки формы

```
Форма (frontend, locale ru|en)
    → POST /api/contact
    → RateLimiter (429 при спаме)
    → Pydantic-валидация (422)
    → Offtopic / AI: тональность + категория + автоответ (язык ответа = язык сообщения)
    → LogRepository + MetricsRepository
    → HTTP 200 + ai_analysis
    → BackgroundTasks → EmailService (владелец + пользователь)
```

AI выполняется до ответа клиенту. Письма уходят в фоне; при сбое SMTP сервис уже ответил 200.

---

## Структура проекта

```
developer-landing-api/
├── app/
│   ├── api/v1/endpoints/     # contact, health, metrics
│   ├── core/                 # config, logging, exceptions
│   ├── db/                   # SQLAlchemy models, session
│   ├── middleware/
│   ├── repositories/         # JSON + MySQL адаптеры
│   ├── schemas/
│   ├── services/             # ai, email, rate_limiter, offtopic
│   └── main.py
├── frontend/
│   ├── index.html
│   ├── css/style.css
│   └── js/main.js, i18n.js
├── postman/
├── .github/workflows/deploy.yml
├── gunicorn.conf.py
└── requirements.txt
```

---

## API

### POST /api/contact

**Запрос:**
```json
{
  "name": "Иван Иванов",
  "phone": "+79991234567",
  "email": "ivan@example.com",
  "comment": "Хочу обсудить разработку CRM для нашей компании",
  "locale": "ru"
}
```

Поле `locale` — `ru` или `en` (язык интерфейса; влияет на fallback-тексты). Язык AI-ответа определяется по тексту `comment`.

**Валидация:** имя 2–100 символов; телефон `+?[0-9]{10,15}`; email с проверкой MX; комментарий 10–2000 символов.

**Успех (200):**
```json
{
  "success": true,
  "message": "Обращение принято! Отвечу в ближайшее время.",
  "request_id": "550e8400-e29b-41d4-a716-446655440000",
  "ai_analysis": {
    "sentiment": "positive",
    "category": "project_inquiry",
    "auto_reply": "…",
    "ai_available": true
  }
}
```

| Код | Ситуация |
|---|---|
| 422 | Ошибка валидации |
| 429 | Rate limit (5 запросов / 15 мин с IP) |
| 500 | Внутренняя ошибка |

**Пример 422** (невалидный email и короткий комментарий):

```bash
curl -X POST http://localhost:8000/api/contact \
  -H "Content-Type: application/json" \
  -d '{"name":"Иван","phone":"+79991234567","email":"bad@","comment":"коротко","locale":"ru"}'
```

```json
{
  "success": false,
  "error": "Ошибка валидации данных",
  "details": [
    { "field": "email", "message": "Домен email не найден или не принимает почту. Проверьте адрес." },
    { "field": "comment", "message": "Напишите хотя бы 10 символов — расскажите подробнее" }
  ]
}
```

Формат 422 единый для всех полей — handler в `app/core/exceptions.py` возвращает `{ field, message }[]`.

**Пример 429** (превышен rate limit — 5 запросов за 15 мин с одного IP):

```json
{
  "success": false,
  "error": "Слишком много запросов. Попробуйте через 15 минут.",
  "retry_after_seconds": 900
}
```

Заголовок ответа: `Retry-After: 900`.

### GET /api/health

```json
{
  "status": "ok",
  "version": "1.0.0",
  "ai_available": true,
  "email_available": true,
  "database_available": true,
  "storage": "mysql",
  "uptime_seconds": 3600
}
```

`storage`: `mysql` или `json`. `database_available` — `true` только при рабочем `DATABASE_URL`.

### GET /api/metrics

Агрегированная статистика обращений (из MySQL или `data/metrics.json`).

```bash
curl http://localhost:8000/api/metrics
```

```json
{
  "total_requests": 42,
  "successful": 38,
  "errors": 1,
  "rate_limited": 3,
  "by_category": {
    "project_inquiry": 20,
    "job_offer": 5,
    "consultation": 8,
    "other": 5
  },
  "by_day": {
    "2026-06-18": 12,
    "2026-06-19": 18,
    "2026-06-20": 12
  }
}
```

Счётчики обновляются в `MetricsRepository` при каждом `POST /api/contact` (total, successful + category, rate_limited при 429).

---

## AI-интеграция

**Провайдер:** OpenRouter · **Модель:** `mistralai/mistral-nemo`

1. Тональность: `positive` / `neutral` / `negative`
2. Категория: `project_inquiry` / `job_offer` / `consultation` / `other`
3. Персонализированный `auto_reply` на языке сообщения пользователя

**Дополнительно:**
- Casual/offtopic («привет как дела») — шаблонный ответ с предложением описать проект (`app/services/offtopic.py`)
- При generic-ответе модели — повторный запрос с уточнённым промптом
- Если OpenRouter недоступен — bilingual fallback, `ai_available: false`

SMTP вынесен в `BackgroundTasks` — ответ формы ~5–8 с вместо ~20 с.

### Промпты (выдержки из `ai_service.py`)

**Основной промпт** (`_PROMPT`) — sentiment + category + auto_reply:

```
Ты — помощник backend-разработчика Артёма Hernandez.
Проанализируй сообщение и верни ТОЛЬКО валидный JSON (без markdown).

Поля:
- sentiment: positive | neutral | negative
- category: project_inquiry | job_offer | consultation | other
- auto_reply: готовый ответ пользователю (2–3 предложения от лица Артёма, обратись по имени)

Язык auto_reply: ТОЛЬКО {language}. Не смешивай языки.

Правила для auto_reply:
1. Если в сообщении УЖЕ есть детали (сфера, стек, сроки, бюджет, интеграции) —
   ОБЯЗАТЕЛЬНО упомяни 1–2 конкретные детали из текста.
2. НЕ пиши «расскажите подробнее», «tell me more» — если человек уже описал задачу.
3. Если сообщение короткое и без сути — вежливо попроси описать задачу.
4. Оффтоп (просто «привет») — мягко верни к теме разработки.
5. Тон: профессионально, по-человечески, без канцелярита.

Плохой пример (слишком общий, детали проигнорированы):
«Привет, Иван! Спасибо за интерес. Расскажите больше о проекте.»

Хороший пример (есть отсылка к деталям):
«Привет, Дмитрий! Система для сети автосервисов с записью и интеграцией с 1С —
понятная задача. MVP к ноябрю звучит реально — давайте созвонимся на этой неделе.»

Имя: {name}
Сообщение: {comment}
```

**Retry-промпт** (`_RETRY_PROMPT`) — если модель дала шаблонный ответ на развёрнутое сообщение:

```
Пользователь уже отправил РАЗВЁРНУТОЕ сообщение. Верни ТОЛЬКО JSON:
{"auto_reply": "..."}

auto_reply на языке: {language}
Имя: {name}

Обязательно:
- Упомяни 1–2 КОНКРЕТНЫЕ детали из сообщения (отрасль, технологии, срок, интеграция, масштаб)
- НЕ проси «рассказать подробнее» / «tell me more» — детали уже есть
- 2–3 предложения от лица Артёма

Сообщение:
{comment}
```

**Post-processing:** фильтрация утечки промпта (`_PROMPT_LEAK_MARKERS`), детекция generic-ответов (`_GENERIC_REPLY_MARKERS`), определение языка ответа по кириллице/латинице в `comment`, offtopic без вызова LLM.

---

## Хранение данных

| Режим | Когда | Где |
|---|---|---|
| JSON | `DATABASE_URL` пустой | `data/logs/`, `data/metrics.json`, `data/rate_limits.json` |
| MySQL | `DATABASE_URL` задан | Таблицы `contacts`, `metrics`, `rate_limits` |

Папка `data/` создаётся автоматически и в `.gitignore` (логи и runtime-данные не в репозитории).

Rate limiting: файловый или MySQL; при ошибке БД — fallback на JSON.

Подробнее про файлы логов, access-log middleware и формат `contacts.json` — см. раздел [Логирование](#логирование).

---

## Frontend

Одностраничный лендинг в `frontend/` — без фреймворков, Vanilla HTML/CSS/JS.

| Компонент | Файл | Описание |
|---|---|---|
| Разметка | `index.html` | Hero, стек, проекты, форма обратной связи |
| Стили | `css/style.css` | Тёмная тема, градиенты, scroll-reveal, кастомный scrollbar |
| Логика формы | `js/main.js` | Валидация, маска телефона `+7 (XXX)-XXX-XXXX`, fetch → API |
| i18n RU/EN | `js/i18n.js` | Словарь переводов, переключатель языка, `localStorage` |

**Форма обратной связи:**
- Клиентская валидация (имя, телефон, email, комментарий 10–2000 символов)
- Маска телефона — только цифры, отправка в API как `+7XXXXXXXXXX`
- Поле `locale` (`ru`/`en`) передаётся вместе с формой
- При 422 — подсветка полей с сообщениями из `details[]`
- При 429 — общая ошибка rate limit

**AI-ответ на экране:**
После успешной отправки форма скрывается, показывается блок «Сообщение отправлено!» с `ai_analysis.auto_reply` из ответа API. Текст проходит `sanitizeAutoReply()` — отфильтровывает утечки промпта на клиенте.

**i18n:** переключатель RU/EN в шапке; все тексты формы, валидации и ошибок — из объекта `I18N`. Язык сохраняется в `localStorage`.

---

## Логирование

| Файл / компонент | Назначение |
|---|---|
| `data/logs/app.log` | Основной лог (INFO+), ротация 10 MB × 5 |
| `data/logs/error.log` | Только ERROR, ротация 5 MB × 3 |
| `data/logs/contacts.json` | Журнал обращений (local mode) — timestamp, request_id, IP, AI-метаданные |
| `RequestLoggingMiddleware` | Access-log каждого HTTP-запроса: IP, method, path, status, duration_ms |

**Пример строки access-log:**
```
2026-06-20 14:32:01 | INFO     | access | 127.0.0.1 | POST   /api/contact                              | 200 | 6234.5ms
```

**Пример записи в `contacts.json`:**
```json
{
  "timestamp": "2026-06-20T11:32:01.123456Z",
  "request_id": "550e8400-e29b-41d4-a716-446655440000",
  "ip": "127.0.0.1",
  "name": "Иван Иванов",
  "phone": "+79991234567",
  "email": "ivan@example.com",
  "comment": "Хочу обсудить разработку CRM...",
  "comment_length": 52,
  "sentiment": "positive",
  "category": "project_inquiry",
  "ai_available": true,
  "email_errors": []
}
```

Конфигурация — `app/core/logging_config.py`, каталог `data/logs/` создаётся при старте.

---

## Безопасность

- **CORS** — `CORSMiddleware`, origins из `ALLOWED_ORIGINS` в `.env` (по умолчанию `*`)
- **Rate limiting** — 5 запросов / 15 мин с IP (`RATE_LIMIT_REQUESTS` / `RATE_LIMIT_WINDOW_SECONDS`); ответ 429 + заголовок `Retry-After`
- **Email MX-проверка** — `email-validator` с `check_deliverability=True`; домен без MX/A-записей → 422
- **Pydantic-валидация** — имя (regex), телефон (`+?[0-9]{10,15}`), комментарий (10–2000)
- **Prompt leak filter** — на backend и frontend отсекаются фрагменты системного промпта в `auto_reply`
- **Secrets** — `.env` в `.gitignore`; ключи OpenRouter/SMTP только через переменные окружения

---

## Деплой

### Production (Beget VPS)

Сервер: `/var/www/developer-landing-api`, сервис `developer-api` (gunicorn + nginx).

**CI/CD:** push в `master` → GitHub Actions (`.github/workflows/deploy.yml`) → SSH → `git pull` → `pip install` → `systemctl restart developer-api`.

Секреты в GitHub: `VPS_HOST`, `VPS_USER`, `VPS_SSH_KEY`.

На сервере в `.env` указывается `DATABASE_URL` к Beget Cloud MySQL (приватная сеть `10.x.x.x`).

### Первичная настройка VPS (один раз)

```bash
cd /var/www/developer-landing-api
python3.11 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env && nano .env
# systemd unit + nginx — см. gunicorn.conf.py
```

---

## curl-примеры

```bash
# Обращение
curl -X POST http://62.217.179.202/api/contact \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Иван Иванов",
    "phone": "+79991234567",
    "email": "ivan@example.com",
    "comment": "Хочу обсудить разработку CRM для нашей компании",
    "locale": "ru"
  }'

curl http://62.217.179.202/api/health
curl http://62.217.179.202/api/metrics
```

---

## Что сделано с помощью AI (Cursor)

Проект разрабатывался в Cursor с использованием AI-ассистента. Ниже — типовые промпты и разбивка по авторству.

- AI-инструмент: Cursor / Antigravity IDE
- LLM: Claude Sonnet (через Cursor), Gemini Flash 3.5 в Antigravity, а также встроенные модели Cursor (в разных этапах разработки)

### Промпты для Cursor / Antigravity (примеры)

Промпты ниже использовались в Cursor и Antigravity IDE (Gemini 3.5 Flash) на разных этапах разработки.

```
Создай FastAPI-проект для лендинга разработчика: POST /api/contact с Pydantic-валидацией,
AI-анализ через OpenRouter, email через SMTP, rate limiting, логирование в JSON.
Структура: endpoints → services → repositories. Swagger на /docs.
```

```
Добавь dual storage: если DATABASE_URL задан — MySQL через SQLAlchemy,
иначе JSON-файлы в data/. LogRepository и MetricsRepository с одинаковым интерфейсом.
```

```
Напиши одностраничный лендинг: HTML + CSS + JS, форма с валидацией,
маска телефона +7, fetch POST /api/contact, показ ai_analysis.auto_reply после отправки.
```

```
Интегрируй OpenRouter (Mistral Nemo): sentiment, category, auto_reply в JSON.
Fallback при недоступности API. BackgroundTasks для SMTP — не блокировать ответ.
```

```
Добавь i18n RU/EN: словарь переводов, переключатель языка, locale в теле запроса.
```

### AI сгенерировал / вручную

В колонке AI-инструменты отмечены задачи, где использовались Cursor и/или Antigravity IDE (Gemini 3.5 Flash) для генерации каркаса и черновиков.

| Компонент | AI-инструменты (Cursor/Antigravity) | Вручную |
|---|---|---|
| Структура проекта, endpoints, schemas | ✅ | |
| Repository + dual storage (каркас) | ✅ | MySQL на Beget, URL-кодирование пароля |
| AI-сервис (каркас + HTTP-клиент) | ✅ | Промпты, retry, leak/generic-фильтры, offtopic |
| Email-сервис (каркас) | ✅ | SMTP mail.ru, шаблоны писем |
| Frontend (HTML/CSS/JS каркас) | ✅ | Тексты лендинга, phone mask fix, i18n-тексты |
| README (черновик) | ✅ | Деплой, CI/CD, prod-URL, разделы по ТЗ |
| Rate limiter | ✅ | Fallback JSON при ошибке MySQL |
| GitHub Actions deploy | | ✅ `.github/workflows/deploy.yml` |
| nginx + gunicorn + systemd на VPS | | ✅ |
| Промпты `_PROMPT` / `_RETRY_PROMPT` | частично | ✅ финальная версия, примеры good/bad |
| Postman-коллекция | ✅ | проверка на prod |

