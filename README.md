# Developer Landing API

Backend-сервис для лендинга разработчика.  
REST API с AI-анализом (Mistral Nemo через OpenRouter), email-уведомлениями (mail.ru), rate limiting, логированием.  
Плюс фронтенд — одностраничный лендинг.

---

## Стэк

| Слой | Технология |
|---|---|
| Backend | Python 3.11, FastAPI, Pydantic v2 |
| AI | OpenRouter API (Mistral Nemo) |
| Email | mail.ru SMTP over SSL |
| Хранение | JSON-файлы (без БД) |
| Документация | Swagger UI (встроен в FastAPI) |
| Frontend | HTML + Vanilla CSS + JavaScript |
| Деплой | Beget VPS, nginx + gunicorn |

---

## Быстрый старт

### 1. Клонировать / скопировать проект

```bash
git clone <repo-url>
cd developer-landing-api
```

### 2. Создать виртуальное окружение и установить зависимости

```bash
python -m venv venv

# Windows
venv\Scripts\activate

# Linux / macOS
source venv/bin/activate

pip install -r requirements.txt
```

### 3. Настроить переменные окружения

```bash
cp .env.example .env
# Отредактировать .env — вставить реальные ключи
```

Минимально необходимые переменные:

| Переменная | Пример | Описание |
|---|---|---|
| `SMTP_USER` | `you@mail.ru` | Логин SMTP |
| `SMTP_PASSWORD` | `app_password` | Пароль SMTP |
| `OWNER_EMAIL` | `you@mail.ru` | Куда приходят уведомления |
| `OPENROUTER_API_KEY` | `sk-or-v1_...` | Ключ OpenRouter API (openrouter.ai) |
| `OPENROUTER_MODEL` | `mistralai/mistral-nemo` | Модель Mistral Nemo (опционально) |

### 4. Запустить локально

```bash
python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

> **Windows:** если команда `uvicorn` не найдена — активируйте venv или используйте `python -m uvicorn` как выше.

Сервис будет доступен:
- Лендинг: http://localhost:8000
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

### 5. Postman (опционально)

Импортируйте коллекцию `postman/Developer-Landing-API.postman_collection.json`.  
Переменная `base_url` по умолчанию: `http://localhost:8000`.

---

## Архитектура и проектные решения

### Слои

```
HTTP Request
    ↓
Endpoints (Controllers)     app/api/v1/endpoints/
    ↓
Services (бизнес-логика)    app/services/
    ↓
Repositories (хранение)     app/repositories/
    ↓
Файловая система            data/
```

| Слой | Ответственность |
|---|---|
| **Endpoints** | HTTP, статус-коды, оркестрация |
| **Services** | AI, email, rate limiting |
| **Repositories** | JSON-логи, метрики |
| **Schemas** | Pydantic-валидация входа/выхода |
| **Core** | config, logging, exception handlers |
| **Middleware** | лог каждого HTTP-запроса |

### Почему выбраны эти технологии

| Решение | Обоснование |
|---|---|
| **Python + FastAPI** | Async-ready, автогенерация OpenAPI/Swagger, строгая валидация через Pydantic v2 |
| **OpenRouter + Mistral Nemo** | Единый API к разным моделям; Nemo — быстрая 12B-модель с хорошим русским |
| **Файлы вместо БД** | Достаточно для MVP: логи, метрики, rate limit без инфраструктуры БД |
| **mail.ru SMTP** | Нативная почта для `.ru`-домена, SSL на порту 465 |
| **BackgroundTasks для email** | Полный цикл сохранён, но пользователь не ждёт ~10–12 сек SMTP |
| **Префикс `/api`** | Совпадает с ТЗ: `POST /api/contact`, `GET /api/health`, `GET /api/metrics` |

### Полный цикл обработки запроса

```
Форма (frontend)
    → POST /api/contact
    → RateLimiter (429 при спаме)
    → Pydantic-валидация (422 при ошибках)
    → AIService: тональность + категория + автоответ
    → LogRepository + MetricsRepository
    → HTTP 200 + ai_analysis (персональный ответ на экран)
    → BackgroundTasks → EmailService (владелец + пользователь, одна SMTP-сессия)
```

AI выполняется **до** ответа клиенту — пользователь видит персональный `auto_reply`.  
Письма уходят **сразу после** в фоне; при сбое SMTP сервис уже ответил 200, ошибка пишется в лог.

---

## Структура проекта

```
developer-landing-api/
├── app/
│   ├── api/v1/
│   │   ├── endpoints/
│   │   │   ├── contact.py       # POST /api/contact
│   │   │   ├── health.py        # GET  /api/health
│   │   │   └── metrics.py       # GET  /api/metrics
│   │   └── router.py
│   ├── core/
│   │   ├── config.py            # Pydantic Settings (.env)
│   │   ├── logging_config.py    # Файловое логирование
│   │   └── exceptions.py        # Кастомные исключения + глобальные хендлеры
│   ├── middleware/
│   │   └── logging_middleware.py # Лог каждого HTTP-запроса
│   ├── repositories/
│   │   ├── log_repository.py    # Хранение обращений в JSON
│   │   └── metrics_repository.py # Статистика в JSON
│   ├── schemas/
│   │   └── contact.py           # Pydantic модели + валидация
│   ├── services/
│   │   ├── ai_service.py        # OpenRouter (Mistral Nemo) + fallback
│   │   ├── email_service.py     # mail.ru SMTP
│   │   └── rate_limiter.py      # Файловый rate limiting
│   └── main.py                  # Точка входа FastAPI
├── frontend/
│   ├── index.html
│   ├── css/style.css
│   └── js/main.js
├── data/                        # Создаётся автоматически
│   ├── logs/                    # app.log, error.log, contacts.json
│   ├── metrics.json
│   └── rate_limits.json
├── postman/
│   └── Developer-Landing-API.postman_collection.json
├── .env                         # Локальные секреты (не в git)
├── .env.example
├── gunicorn.conf.py
└── requirements.txt
```

**Архитектурный паттерн:** Controllers (endpoints) → Services → Repositories

---

## API Эндпоинты

### POST /api/contact

Принимает обращение, выполняет AI-анализ, ставит email в очередь на отправку.

**Запрос:**
```json
{
  "name": "Иван Иванов",
  "phone": "+79991234567",
  "email": "ivan@example.com",
  "comment": "Хочу обсудить разработку CRM для нашей компании"
}
```

**Валидация:**
- `name`: 2–100 символов, только буквы/дефис
- `phone`: regex `^\+?[0-9]{10,15}$`, очищается от пробелов и скобок
- `email`: стандартная email-валидация
- `comment`: 10–2000 символов

**Успешный ответ (200):**
```json
{
  "success": true,
  "message": "Обращение принято! Отвечу в ближайшее время.",
  "request_id": "550e8400-e29b-41d4-a716-446655440000",
  "ai_analysis": {
    "sentiment": "positive",
    "category": "project_inquiry",
    "auto_reply": "Добрый день, Иван! Спасибо за интерес — готов обсудить детали проекта.",
    "ai_available": true
  }
}
```

**Коды ошибок:**
| Код | Ситуация |
|---|---|
| 422 | Ошибка валидации (возвращает поле + сообщение) |
| 429 | Превышен rate limit (5 запросов / 15 мин с IP) |
| 500 | Внутренняя ошибка |

---

### GET /api/health

```json
{
  "status": "ok",
  "version": "1.0.0",
  "ai_available": true,
  "email_available": true,
  "uptime_seconds": 3600
}
```

---

### GET /api/metrics

```json
{
  "total_requests": 42,
  "successful": 38,
  "errors": 2,
  "rate_limited": 2,
  "by_category": {
    "project_inquiry": 20,
    "job_offer": 10,
    "consultation": 5,
    "other": 3
  },
  "by_day": {
    "2026-06-19": 15
  }
}
```

---

## AI-интеграция

**Провайдер:** OpenRouter API  
**Модель:** `mistralai/mistral-nemo` (Mistral Nemo, 12B)

**Что делает:**
1. Определяет тональность сообщения (`positive` / `neutral` / `negative`)
2. Классифицирует тип запроса (`project_inquiry` / `job_offer` / `consultation` / `other`)
3. Генерирует персонализированный автоответ от лица Разработчика

**Промпт:**
```
Проанализируй входящее сообщение и верни ТОЛЬКО валидный JSON:
{
  "sentiment": "positive|neutral|negative",
  "category": "project_inquiry|job_offer|consultation|other",
  "auto_reply": "Ответ от лица Разработчика, 2-3 предложения, обратись по имени"
}
```

**Graceful fallback:**  
Если OpenRouter недоступен (нет ключа, таймаут, невалидный JSON) — возвращается дефолтный ответ, поле `ai_available: false`. Письма отправляются в любом случае, сервис не падает.

**Оптимизация скорости:** SMTP-отправка вынесена в `BackgroundTasks` — пользователь получает AI-ответ за ~5–8 сек вместо ~20 сек.

---

## Хранение данных

Всё хранится в папке `data/` в виде JSON/log файлов:

| Файл | Содержимое |
|---|---|
| `data/logs/app.log` | Общий лог (ротация 10 MB, 5 копий) |
| `data/logs/error.log` | Только ошибки (ротация 5 MB, 3 копии) |
| `data/logs/contacts.json` | Все обращения (последние 10 000) |
| `data/metrics.json` | Агрегированная статистика |
| `data/rate_limits.json` | Счётчики rate limiting по IP |

---

## Rate Limiting

Файловый, без Redis. 5 запросов за 15 минут с одного IP.  
При превышении: `HTTP 429` с заголовком `Retry-After`.  
Стейт сохраняется между перезапусками.

---

## Деплой

### Beget VPS (production)

```bash
# 1. Загрузить проект на сервер
scp -r . user@server:/var/www/developer-api

# 2. Создать venv и установить зависимости
cd /var/www/developer-api
python3.11 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# 3. Настроить .env
cp .env.example .env && nano .env

# 4. Запустить через gunicorn
gunicorn app.main:app -c gunicorn.conf.py

# 5. Настроить nginx как reverse proxy:
# location /api { proxy_pass http://127.0.0.1:8000; }
# location /    { proxy_pass http://127.0.0.1:8000; }
```

### Локальный доступ через ngrok (демо для проверяющих)

```bash
# Терминал 1 — сервер
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000

# Терминал 2 — туннель
ngrok http 8000
```

Публичный URL из ngrok (например `https://xxxx.ngrok-free.app`) можно указать в README или PR как рабочий API.

---

## curl-примеры

```bash
# Отправить обращение (/api/contact — как в ТЗ)
curl -X POST http://localhost:8000/api/contact \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Иван Иванов",
    "phone": "+79991234567",
    "email": "ivan@example.com",
    "comment": "Хочу обсудить разработку CRM для нашей компании"
  }'

# Проверить статус
curl http://localhost:8000/api/health

# Посмотреть статистику
curl http://localhost:8000/api/metrics
```

---

## Что сделано с помощью AI

Код написан с использованием AI-ассистентов (Cursor/Antigravity IDE). AI генерировал:
- Структуру проекта и шаблоны endpoints/services/repositories
- HTML/CSS/JS для фронтенда
- Черновики README и Postman-коллекции

Что настраивалось и проверялось вручную:
- Реальные SMTP-параметры и проверка подключения mail.ru
- Промпты для Mistral Nemo (несколько итераций для стабильного JSON)
- Бизнес-логика fallback-сценариев и BackgroundTasks для email
- Миграция с Groq → OpenRouter, оптимизация времени ответа формы
- Тексты на сайте (биография, проекты, описания)
- Rate limiting, обработка ошибок, валидация полей формы

---