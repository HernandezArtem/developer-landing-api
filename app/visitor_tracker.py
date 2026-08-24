"""
Visitor Tracker — интеграция для FastAPI.

Подключение в main.py:

    from app.visitor_tracker import setup_visitor_tracker

    setup_visitor_tracker(
        app,
        api_url=settings.TRACKER_API_URL,
        secret_key=settings.TRACKER_SECRET_KEY,
    )

В index.html перед </body>:

    <script src="/tracker-config.js"></script>
    <script src="/tracker.js"></script>

Зависимость: httpx (уже в requirements.txt)
"""

from __future__ import annotations

import asyncio
import hashlib
import hmac
import json
import re
import time
import uuid
from datetime import datetime, timezone
from typing import Callable, Optional

import httpx
from fastapi import FastAPI
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import FileResponse, Response

VISITOR_COOKIE = "_vt_visitor_id"
SESSION_COOKIE = "_vt_session_id"
COOKIE_MAX_AGE = 31536000
# httponly=False — JS синхронизирует cookie с localStorage
COOKIE_HTTPONLY = False

SKIP_EXTENSIONS = re.compile(
    r"\.(css|js|mjs|map|png|jpe?g|gif|webp|svg|ico|woff2?|ttf|eot|mp4|webm|json|xml|txt)$",
    re.IGNORECASE,
)


def _normalize_ip(ip: str) -> str:
    value = (ip or "").strip()
    if not value:
        return "0.0.0.0"
    if value in ("::1", "0:0:0:0:0:0:0:1"):
        return "127.0.0.1"
    if value.lower().startswith("::ffff:"):
        mapped = value[7:]
        parts = mapped.split(".")
        if len(parts) == 4 and all(part.isdigit() and 0 <= int(part) <= 255 for part in parts):
            return mapped
    return value


def _get_client_ip(request: Request) -> str:
    for header in ("cf-connecting-ip", "x-real-ip", "x-forwarded-for"):
        value = request.headers.get(header)
        if value:
            if header == "x-forwarded-for":
                value = value.split(",")[0].strip()
            return _normalize_ip(value)
    if request.client:
        return _normalize_ip(request.client.host)
    return "0.0.0.0"


def _hmac_hex(message: str, secret_key: str) -> str:
    return hmac.new(secret_key.encode(), message.encode(), hashlib.sha256).hexdigest()


def _get_or_set_cookie(request: Request, name: str, response: Optional[Response] = None) -> str:
    value = request.cookies.get(name)
    if value and len(value) >= 8:
        return value

    value = str(uuid.uuid4())
    if response is not None:
        response.set_cookie(
            key=name,
            value=value,
            max_age=COOKIE_MAX_AGE,
            httponly=COOKIE_HTTPONLY,
            samesite="lax",
        )
    return value


TRACKED_PATHS = frozenset({
    "/",
    "/api/contact",
    "/api/metrics",
    "/docs",
    "/api/health",
})


def _normalize_path(path: str) -> str:
    path = path or "/"
    while "//" in path:
        path = path.replace("//", "/")
    path = path.rstrip("/") or "/"
    return path


MONITOR_USER_AGENT = "TgBot-SiteMonitor"


def _is_monitor_request(request: Request) -> bool:
    return MONITOR_USER_AGENT in request.headers.get("user-agent", "")


def _should_track(request: Request) -> bool:
    if _is_monitor_request(request):
        return False

    path = _normalize_path(request.url.path)
    if path not in TRACKED_PATHS:
        return False

    if path == "/api/contact":
        if request.method not in ("GET", "HEAD", "POST"):
            return False
    elif request.method not in ("GET", "HEAD"):
        return False

    if SKIP_EXTENSIONS.search(path):
        return False

    return True


async def _send_server_track(
    *,
    api_url: str,
    secret_key: str,
    ip: str,
    user_agent: str,
    referer: str,
    page_url: str,
    http_method: str,
    session_id: str,
    visitor_id: str,
    cookies: str,
) -> None:
    payload = {
        "type": "server",
        "server": {
            "ip": ip,
            "userAgent": user_agent,
            "referer": referer,
            "pageUrl": page_url,
            "httpMethod": http_method,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "sessionId": session_id,
            "cookies": cookies,
            "visitorId": visitor_id,
        },
    }

    body = json.dumps(payload, ensure_ascii=False, separators=(",", ":"))
    timestamp = str(int(time.time() * 1000))
    signature = _hmac_hex(body, secret_key)

    headers = {
        "Content-Type": "application/json",
        "X-Secret-Key": secret_key,
        "X-Signature": signature,
        "X-Timestamp": timestamp,
        "X-Tracker-Source": "fastapi-server",
        "User-Agent": "VisitorTrackerFastAPI/1.0",
    }

    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            await client.post(api_url, content=body, headers=headers)
    except Exception:
        pass


class VisitorTrackerMiddleware(BaseHTTPMiddleware):
    def __init__(
        self,
        app,
        api_url: str,
        secret_key: str,
        track_filter: Optional[Callable[[Request], bool]] = None,
    ):
        super().__init__(app)
        self.api_url = api_url
        self.secret_key = secret_key
        self.track_filter = track_filter or _should_track

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        response = await call_next(request)

        if not self.track_filter(request):
            return response

    # Rate limit / слишком много запросов — форму режем, в Telegram не трекаем
        if response.status_code == 429:
            return response


        content_type = response.headers.get("content-type", "")
        if "text/html" in content_type:
            response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
            response.headers["Pragma"] = "no-cache"

        visitor_id = request.cookies.get(VISITOR_COOKIE) or str(uuid.uuid4())
        session_id = request.cookies.get(SESSION_COOKIE) or str(uuid.uuid4())

        if VISITOR_COOKIE not in request.cookies:
            response.set_cookie(
                VISITOR_COOKIE,
                visitor_id,
                max_age=COOKIE_MAX_AGE,
                httponly=COOKIE_HTTPONLY,
                samesite="lax",
            )
        if SESSION_COOKIE not in request.cookies:
            response.set_cookie(
                SESSION_COOKIE,
                session_id,
                max_age=COOKIE_MAX_AGE,
                httponly=COOKIE_HTTPONLY,
                samesite="lax",
            )

        cookies_str = "; ".join(f"{k}={v}" for k, v in request.cookies.items())
        page_url = str(request.url)
        referer = request.headers.get("referer", "")

        asyncio.create_task(
            _send_server_track(
                api_url=self.api_url,
                secret_key=self.secret_key,
                ip=_get_client_ip(request),
                user_agent=request.headers.get("user-agent", ""),
                referer=referer,
                page_url=page_url,
                http_method=request.method,
                session_id=session_id,
                visitor_id=visitor_id,
                cookies=cookies_str,
            )
        )

        return response


def setup_visitor_tracker(
    app: FastAPI,
    *,
    api_url: str,
    secret_key: str,
    tracker_js_path: Optional[str] = None,
    track_filter: Optional[Callable[[Request], bool]] = None,
) -> None:
    """
    Подключает middleware и эндпоинты /tracker-config.js и /tracker.js
    """
    app.add_middleware(
        VisitorTrackerMiddleware,
        api_url=api_url,
        secret_key=secret_key,
        track_filter=track_filter,
    )

    @app.get("/tracker-config.js", include_in_schema=False)
    async def tracker_config(request: Request) -> Response:
        visitor_id = request.cookies.get(VISITOR_COOKIE, "")
        session_id = request.cookies.get(SESSION_COOKIE, "")

        config: dict = {"apiUrl": api_url}

        if visitor_id and session_id and len(visitor_id) >= 8 and len(session_id) >= 8:
            config["sessionId"] = session_id
            config["visitorId"] = visitor_id
            config["clientToken"] = _hmac_hex(f"{session_id}|{visitor_id}|client", secret_key)

        body = f"window.__VISITOR_TRACKER__={json.dumps(config, ensure_ascii=False)};"
        return Response(content=body, media_type="application/javascript")

    @app.get("/tracker-token", include_in_schema=False)
    async def tracker_token(visitorId: str = "", sessionId: str = "") -> Response:
        """Токен для ID из localStorage (когда они не совпадают с cookie)."""
        visitor_id = (visitorId or "").strip()
        session_id = (sessionId or "").strip()
        if len(visitor_id) < 8 or len(session_id) < 8:
            return Response(
                content='{"error":"invalid ids"}',
                status_code=400,
                media_type="application/json",
            )

        token = _hmac_hex(f"{session_id}|{visitor_id}|client", secret_key)
        body = json.dumps(
            {"clientToken": token, "visitorId": visitor_id, "sessionId": session_id},
            ensure_ascii=False,
        )
        return Response(content=body, media_type="application/json")

    js_path = tracker_js_path

    @app.get("/tracker.js", include_in_schema=False)
    async def tracker_js() -> Response:
        if js_path:
            return FileResponse(js_path, media_type="application/javascript")
        return Response(
            content=_DEFAULT_TRACKER_JS,
            media_type="application/javascript",
        )


_DEFAULT_TRACKER_JS = r"""
(function () {
  'use strict';
  var LS_VISITOR = '_vt_visitor_id';
  var LS_SESSION = '_vt_session_id';
  var COOKIE_MAX_AGE = 31536000;
  var config = window.__VISITOR_TRACKER__ || {};
  var apiUrl = config.apiUrl;
  var lastSentAt = 0;
  var MIN_INTERVAL_MS = 2000;
  var trackingSent = false;
  var TRACKED_PATHS = ['/', '/api/contact', '/api/metrics', '/docs', '/api/health'];
  if (!apiUrl) return;
  function uuid() {
    if (window.crypto && crypto.randomUUID) return crypto.randomUUID();
    return 'xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx'.replace(/[xy]/g, function (c) {
      var r = (Math.random() * 16) | 0;
      var v = c === 'x' ? r : (r & 0x3) | 0x8;
      return v.toString(16);
    });
  }
  function lsGet(key) {
    try {
      var value = localStorage.getItem(key);
      return value && value.length >= 8 ? value : '';
    } catch (e) { return ''; }
  }
  function lsSet(key, value) {
    try { localStorage.setItem(key, value); } catch (e) {}
  }
  function setCookie(name, value) {
    try {
      document.cookie = name + '=' + encodeURIComponent(value) +
        '; path=/; max-age=' + COOKIE_MAX_AGE + '; samesite=lax';
    } catch (e) {}
  }
  function resolveIds() {
    var visitorId = lsGet(LS_VISITOR) || config.visitorId || uuid();
    var sessionId = lsGet(LS_SESSION) || config.sessionId || uuid();
    lsSet(LS_VISITOR, visitorId);
    lsSet(LS_SESSION, sessionId);
    setCookie(LS_VISITOR, visitorId);
    setCookie(LS_SESSION, sessionId);
    return { visitorId: visitorId, sessionId: sessionId };
  }
  function normalizePath(pathname) {
    var path = (pathname || '/').replace(/\/+/g, '/').replace(/\/$/, '');
    return path || '/';
  }
  function isTrackedPath() {
    return TRACKED_PATHS.indexOf(normalizePath(window.location.pathname)) !== -1;
  }
  function collectClientData() {
    return {
      screenWidth: screen.width || 0,
      screenHeight: screen.height || 0,
      language: navigator.language || navigator.userLanguage || '',
      timezone: (function () {
        try { return Intl.DateTimeFormat().resolvedOptions().timeZone || ''; }
        catch (e) { return ''; }
      })(),
      platform: navigator.platform || '',
      deviceMemory: navigator.deviceMemory !== undefined ? navigator.deviceMemory : undefined,
      hardwareConcurrency: navigator.hardwareConcurrency || 0,
      touchSupport: 'ontouchstart' in window || navigator.maxTouchPoints > 0,
      cookiesEnabled: navigator.cookieEnabled,
    };
  }
  function fetchClientToken(visitorId, sessionId, done) {
    if (config.clientToken && visitorId === config.visitorId && sessionId === config.sessionId) {
      done(config.clientToken);
      return;
    }
    var url = '/tracker-token?visitorId=' + encodeURIComponent(visitorId) +
      '&sessionId=' + encodeURIComponent(sessionId);
    var xhr = new XMLHttpRequest();
    xhr.open('GET', url, true);
    xhr.onload = function () {
      if (xhr.status < 200 || xhr.status >= 300) { done(''); return; }
      try { done(JSON.parse(xhr.responseText).clientToken || ''); }
      catch (e) { done(''); }
    };
    xhr.onerror = function () { done(''); };
    xhr.send();
  }
  function sendTracking() {
    if (!isTrackedPath()) return;
    var now = Date.now();
    if (trackingSent || now - lastSentAt < MIN_INTERVAL_MS) return;
    trackingSent = true;
    lastSentAt = now;
    var ids = resolveIds();
    fetchClientToken(ids.visitorId, ids.sessionId, function (clientToken) {
      if (!clientToken) { trackingSent = false; return; }
      var payload = {
        type: 'client',
        server: {
          ip: '', userAgent: navigator.userAgent || '', referer: document.referrer || '',
          pageUrl: window.location.href, httpMethod: 'GET',
          timestamp: new Date().toISOString(), sessionId: ids.sessionId,
          cookies: document.cookie || '', visitorId: ids.visitorId,
        },
        client: collectClientData(),
      };
      var xhr = new XMLHttpRequest();
      xhr.open('POST', apiUrl, true);
      xhr.setRequestHeader('Content-Type', 'application/json');
      xhr.setRequestHeader('X-Client-Token', clientToken);
      xhr.setRequestHeader('X-Timestamp', String(Date.now()));
      xhr.send(JSON.stringify(payload));
    });
  }
  window.addEventListener('pageshow', function () { sendTracking(); });
})();
""".strip()
