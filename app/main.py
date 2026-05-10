"""
AI Chatbot Service - FastAPI Application Entry Point
"""

import os
import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from slowapi.errors import RateLimitExceeded
from slowapi import _rate_limit_exceeded_handler
from app.config import get_settings
from app.core.ai_client import ai_client
from app.core.rate_limiter import limiter
from app.modules.auth.router import router as auth_router
from fastapi.staticfiles import StaticFiles

settings = get_settings()
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup and shutdown events."""
    yield
    await ai_client.close()


app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="Universal AI Chatbot-as-a-Service. Connect any system to get an intelligent chatbot.",
    docs_url="/docs",
    redoc_url=None,
    lifespan=lifespan,
)

# Rate limiting
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# CORS — origins loaded from ALLOWED_ORIGINS in .env
allowed_origins = settings.allowed_origins_list or ["*"]

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

API_PREFIX = "/api/v1"

# Modular API routers
from app.modules.organizations.router import router as org_router
from app.modules.subscriptions.router import router as sub_router
from app.modules.tokens.router import router as token_router
from app.modules.ai_providers.router import router as ai_provider_router
from app.modules.chatbots.router import router as chatbot_router
from app.modules.knowledge.router import router as knowledge_router
from app.modules.chat.router import router as chat_router
from app.modules.escalation.router import router as escalation_router
from app.modules.language.router import router as language_router
from app.modules.analytics.router import router as analytics_router

app.include_router(auth_router,        prefix=API_PREFIX)
app.include_router(org_router,         prefix=API_PREFIX)
app.include_router(sub_router,         prefix=API_PREFIX)
app.include_router(token_router,       prefix=API_PREFIX)
app.include_router(ai_provider_router, prefix=API_PREFIX)
app.include_router(chatbot_router,     prefix=API_PREFIX)
app.include_router(knowledge_router,   prefix=API_PREFIX)
app.include_router(chat_router,        prefix=API_PREFIX)
app.include_router(escalation_router,  prefix=API_PREFIX)
app.include_router(language_router,    prefix=API_PREFIX)
app.include_router(analytics_router,   prefix=API_PREFIX)


@app.get("/redoc", include_in_schema=False)
async def custom_redoc():
    """Self-hosted ReDoc — no CDN required."""
    from fastapi.responses import HTMLResponse
    html = """<!DOCTYPE html>
<html>
  <head>
    <title>AI Chatbot Service - ReDoc</title>
    <meta charset="utf-8"/>
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <link href="https://fonts.googleapis.com/css?family=Montserrat:300,400,700|Roboto:300,400,700" rel="stylesheet">
    <style>body { margin: 0; padding: 0; }</style>
  </head>
  <body>
    <redoc spec-url='/openapi.json'></redoc>
    <script src="/redoc.standalone.js"></script>
  </body>
</html>"""
    return HTMLResponse(html)


@app.get("/health")
async def health_check():
    admin_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "admin-dashboard", "dist")
    return {
        "status": "healthy",
        "service": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "admin_dir": admin_dir,
        "admin_exists": os.path.exists(admin_dir),
        "admin_files": os.listdir(admin_dir) if os.path.exists(admin_dir) else [],
    }


BASE_DIR   = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ADMIN_DIR  = os.path.join(BASE_DIR, "admin-dashboard", "dist")
FRONTEND_DIR = os.path.join(BASE_DIR, "frontend")

# Admin dashboard — React SPA served at /admin
if os.path.exists(ADMIN_DIR):
    from fastapi.responses import FileResponse

    app.mount("/admin/assets", StaticFiles(directory=os.path.join(ADMIN_DIR, "assets")), name="admin-assets")

    @app.get("/admin/{full_path:path}")
    @app.get("/admin")
    async def serve_admin(full_path: str = ""):
        return FileResponse(os.path.join(ADMIN_DIR, "index.html"))

# Frontend chat widget — catch-all (must be LAST)
if os.path.exists(FRONTEND_DIR):
    app.mount("/", StaticFiles(directory=FRONTEND_DIR, html=True), name="frontend")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host="0.0.0.0", port=9000, reload=True, log_level="info", access_log=True)
