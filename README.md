# Developer Landing API

Backend-сервис и одностраничный лендинг портфолио разработчика.

**Production:** http://62.217.179.202  
**Репозиторий:** https://github.com/HernandezArtem/developer-landing-api

REST API с AI-анализом (Mistral Nemo через OpenRouter), email-уведомлениями (mail.ru), rate limiting и двойным хранением данных (MySQL на сервере / JSON локально). Фронтенд — RU/EN с переключателем языка.

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

## Быстрый старт

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
- ReDoc: http://localhost:8000/redoc

### 5. Postman

Импортируйте `postman/Developer-Landing-API.postman_collection.json`.  
Переменная `base_url`: `http://localhost:8000` или `http://62.217.179.202`.

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

---

## Хранение данных

| Режим | Когда | Где |
|---|---|---|
| JSON | `DATABASE_URL` пустой | `data/logs/`, `data/metrics.json`, `data/rate_limits.json` |
| MySQL | `DATABASE_URL` задан | Таблицы `contacts`, `metrics`, `rate_limits` |

Папка `data/` создаётся автоматически и в `.gitignore` (логи и runtime-данные не в репозитории).

Rate limiting: файловый или MySQL; при ошибке БД — fallback на JSON.

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

## Что сделано с помощью AI

Код и документация частично сгенерированы в Cursor/Antigravity IDE: структура проекта, endpoints, фронтенд, черновики README.

Вручную настроено и доведено до prod: SMTP mail.ru, промпты и fallback AI, MySQL + dual storage, i18n, rate limiting, CI/CD на Beget, тексты лендинга, phone mask, offtopic-логика.
