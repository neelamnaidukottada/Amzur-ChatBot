"""FastAPI application entry point."""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.settings import settings
from app.api import chat, auth, data
from app.core.init_db import init_db

# Try to initialize database, but don't fail if not available
try:
    init_db()
except Exception as e:
    print(f"⚠️  Warning: Could not initialize database on startup: {e}")
    print("   Database will be initialized on first request")

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

# Include routers
app.include_router(auth.router)
app.include_router(chat.router)
app.include_router(data.router)


@app.get("/health")
async def health_check() -> dict:
    """Health check endpoint."""
    return {"status": "ok"}


@app.get("/api/diagnostic")
async def diagnostic() -> dict:
    """Diagnostic endpoint to debug CORS and connection issues."""
    return {
        "status": "ok",
        "backend_running": True,
        "cors_enabled": True,
        "allowed_origins": settings.ALLOWED_ORIGINS,
        "litellm_proxy": settings.LITELLM_PROXY_URL,
        "environment": settings.ENVIRONMENT,
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
