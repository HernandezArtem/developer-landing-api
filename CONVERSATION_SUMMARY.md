# Conversation Summary — developer-landing-api

## Project
- **Repo:** `D:/antiprojects/developer-landing-api`
- **Prod:** http://62.217.179.202
- **GitHub:** https://github.com/HernandezArtem/developer-landing-api
- **Stack:** FastAPI, OpenRouter (Mistral Nemo), mail.ru SMTP, MySQL (prod) / JSON (local), vanilla frontend with RU/EN i18n, CI/CD to Beget VPS

## User Goals (arc)
1. Final audit vs test assignment (ТЗ) before submission — **done, ready to submit**
2. README completeness (7 TZ sections, AI prompts, architecture, Cursor/Antigravity credits)
3. Cleanup test files
4. Various bug fixes (AI replies, email validation, rate limit, i18n)
5. **Latest open issue:** i18n name shows literal `hero.firstName` / `hero.fullName` / `hero.initials` on EN site after name translation fix

---

## TZ Status
**Assignment fully covered.** Prod health OK (MySQL, AI, SMTP). README ~550 lines with all required sections. Postman + curl + deploy URL present.

---

## Key Changes Made

### Removed
- `test_api.py`
- `scripts/run_tests.py`

### Backend
- `app/core/request_utils.py` — `get_client_ip()` from `X-Forwarded-For` / `X-Real-IP`
- `app/core/exceptions.py` — uses `get_client_ip`; **had bug:** removed `RequestValidationError` import → 502 on prod; **fixed**
- `app/schemas/contact.py` — locale-first validation; bilingual error messages; email as `str` (not `EmailStr`); ASCII-only email (`email_latin`); `_ASCII_EMAIL_RE`
- `app/services/offtopic.py` — `is_nonsense_message()`, `nonsense_reply()`
- `app/services/ai_service.py` — prompt rewrite (no "assistant" persona); assistant leak filter; nonsense path before OpenRouter

### Frontend
- `frontend/index.html` — Bitrix logo `img/bitrix.png`; i18n keys for name: `hero.firstName`, `hero.lastName`, `hero.fullName`, `hero.initials`, `hero.role`
- `frontend/js/i18n.js` — keys: `firstName`, `lastName`, `fullName`, `initials` under `hero` (RU: Артём/АН, EN: Artem/AH); Cursor/Antigravity + Gemini Flash 3.5 in README section
- `frontend/js/main.js` — `serverFieldError()` for 422 i18n; ASCII email regex; `cleanValidationMessage()`

### Docs
- `README.md` — full TZ alignment, prod URL, AI prompts, patterns, security, frontend, logging, "Что сделано с помощью AI"

---

## Bugs Fixed
| Issue | Fix |
|---|---|
| Prod 502 after IP fix | Restored `from fastapi.exceptions import RequestValidationError` in `exceptions.py` |
| AI says "я помощник Артёма" | Prompt + nonsense template + `_ASSISTANT_LEAK_MARKERS` |
| Email errors in English on RU site | Removed `EmailStr`, custom validator |
| Email errors in Russian on EN site | Locale-aware `_MSGS` in `contact.py` + `serverFieldError()` on frontend |
| Cyrillic/mixed email allowed | `_ASCII_EMAIL_RE` + `email_latin` |
| Bitrix icon broken (404) | Path `img/bitrix.png` not `/frontend/img/...` |
| Rate limit shared IP (127.0.0.1) | `get_client_ip()` — nginx headers still recommended on VPS |

---

## Open Bug — MUST FIX NEXT

**Symptom:** After i18n name fix, hero shows literal text `hero.firstName`, `hero.lastName`, `hero.fullName`, `hero.initials` instead of "Artem" / "Артём".

**Verified:**
- Prod `i18n.js` **does contain** `firstName`, `lastName`, `fullName`, `initials` under `hero` for both `ru` and `en`
- Prod `index.html` has `data-i18n="hero.firstName"` etc.
- `t('hero.firstName')` logic should work if key is passed correctly

**Likely cause:** `applyI18n()` uses `el.dataset.i18n` which may not reliably return `"hero.firstName"` (dataset/camelCase quirks). When lookup fails, `t()` returns the key string unchanged → displayed as `hero.firstName`.

**Recommended fix (not yet applied):**
1. In `frontend/js/i18n.js` `applyI18n()`, use `el.getAttribute('data-i18n')` instead of `el.dataset.i18n`
2. Optionally use flat keys (`heroFirstName`) without dots, or fallback: if `t(key) === key`, keep existing `textContent`
3. Same for `data-i18n-html`, `data-i18n-placeholder`, `data-i18n-aria` if needed

**Last action:** Attempted StrReplace on i18n.js failed (no-op). **Fix was NOT completed.**

---

## Rate Limiting (user questions)
- 5 requests / 15 min per IP (`RATE_LIMIT_REQUESTS=5`, `RATE_LIMIT_WINDOW_SECONDS=900`)
- Stored in MySQL `rate_limits` on prod, JSON locally
- User hit 429 during testing — normal; window resets after 15 min from first request in window
- VPN doesn't always change effective IP; phone on same WiFi = same IP
- phpMyAdmin "Очистить" = TRUNCATE — clears table rows (contacts/metrics/rate_limits)

---

## Git State (last check)
- Branch `master`, clean working tree, up to date with origin
- Latest commits: `7f770c4 Update`, `60e6dbb Update`

---

## User Preferences
- Do NOT commit unless explicitly asked
- Do NOT push `.env`
- Russian communication preferred
- Minimal scope changes

---

## What Next Assistant Should Do
1. **Fix i18n `hero.firstName` display bug** in `frontend/js/i18n.js` (getAttribute + fallback)
2. Verify locally and remind user to commit + push for prod
3. Optional: nginx `proxy_set_header X-Real-IP` / `X-Forwarded-For` on VPS if not configured
