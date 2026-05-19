"""FastAPI application entry point."""

import logging
import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.settings import settings
from app.api import chat, auth, data, research, tictactoe
from app.core.init_db import init_db

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Try to initialize database, but don't fail if not available
try:
    init_db()
    logger.info("✅ Database initialized successfully")
except Exception as e:
    logger.warning(f"⚠️  Database initialization warning: {e}")
    logger.info("   Database will be initialized on first request")

app = FastAPI(
    title=settings.APP_NAME,
    description="Simple chatbot with LangChain and LiteLLM",
    version="1.0.0",
)

# CORS middleware - Allow frontend to communicate with backend
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["Content-Type", "Authorization"],
    expose_headers=["Content-Type"],
    max_age=600,
)

logger.info("✅ CORS Middleware configured")
logger.info(f"   Allowed origins: {settings.ALLOWED_ORIGINS}")

# Include routers
app.include_router(auth.router)
logger.info("✅ Auth router loaded: /api/auth/*")

app.include_router(chat.router)
logger.info("✅ Chat router loaded: /api/chat/*")

app.include_router(data.router)
logger.info("✅ Data router loaded: /api/data/*")

app.include_router(research.router)
logger.info("✅ Research router loaded: /api/research/*")

app.include_router(tictactoe.router)
logger.info("✅ TicTacToe router loaded: /api/games/tictactoe/*")


@app.on_event("startup")
async def log_registered_routes() -> None:
    """Log the active process and the registered game routes on startup."""
    game_routes = sorted(
        route.path for route in app.routes if route.path.startswith("/api/games/tictactoe")
    )
    logger.info("✅ Backend startup complete in PID %s", os.getpid())
    logger.info("✅ Registered TicTacToe routes: %s", game_routes)


@app.get("/health")
async def health_check() -> dict:
    """Health check endpoint."""
    return {"status": "ok"}


@app.get("/api/diagnostic")
async def diagnostic() -> dict:
    """Diagnostic endpoint to debug CORS and connection issues."""
    logger.info("📋 Diagnostic endpoint called")
    return {
        "status": "ok",
        "backend_running": True,
        "cors_enabled": True,
        "allowed_origins": settings.ALLOWED_ORIGINS,
        "litellm_proxy": settings.LITELLM_PROXY_URL,
        "environment": settings.ENVIRONMENT,
        "message": "✅ Backend is running correctly! Frontend should be able to connect."
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
