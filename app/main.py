from pathlib import Path
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.exceptions import RequestValidationError
from fastapi.responses import Response

from app.core.config import settings
from app.core.logging_config import setup_logging
from app.core.exceptions import (
    RateLimitExceeded,
    InvalidAPIKey,
    validation_exception_handler,
    rate_limit_exception_handler,
    invalid_api_key_handler,
    global_exception_handler,
)
from app.middleware.logging_middleware import RequestLoggingMiddleware
from app.api.v1.router import api_router
from app.db import init_db

setup_logging()
init_db()

app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="Backend API лендинга.",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["*"],
)
app.add_middleware(RequestLoggingMiddleware)

app.add_exception_handler(RequestValidationError, validation_exception_handler)
app.add_exception_handler(RateLimitExceeded, rate_limit_exception_handler)
app.add_exception_handler(InvalidAPIKey, invalid_api_key_handler)
app.add_exception_handler(Exception, global_exception_handler)

# API routes must be registered BEFORE the static mount
app.include_router(api_router, prefix="/api")


@app.get("/js/config.js", include_in_schema=False)
def frontend_config() -> Response:
    """Expose CONTACT_API_KEY to the landing form (same origin only)."""
    key = settings.CONTACT_API_KEY.replace("\\", "\\\\").replace('"', '\\"')
    body = f'window.SITE_CONFIG={{contactApiKey:"{key}"}};'
    return Response(
        content=body,
        media_type="application/javascript",
        headers={"Cache-Control": "no-store"},
    )

# Mount frontend at root LAST — API routes above take priority.
# html=True makes css/js relative paths resolve from frontend/
_frontend = Path("frontend")
if _frontend.exists():
    app.mount("/", StaticFiles(directory="frontend", html=True), name="static")
