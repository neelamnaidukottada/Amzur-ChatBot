from pathlib import Path

from pydantic import ConfigDict
from pydantic_settings import BaseSettings


BASE_DIR = Path(__file__).resolve().parents[2]
ENV_FILE = BASE_DIR / ".env"


class Settings(BaseSettings):
    """Application configuration from environment variables."""

    model_config = ConfigDict(extra='ignore', env_file=str(ENV_FILE), case_sensitive=True)

    # App
    APP_NAME: str = "amzur-simple-chatbot"
    ENVIRONMENT: str = "development"

    # Amzur LiteLLM Proxy
    LITELLM_PROXY_URL: str = "https://litellm.amzur.com"
    LITELLM_API_KEY: str = "sk-YLmZIK6subdXeSdRWnyCXg"  # Set via environment variable or .env
    LLM_MODEL: str = "gpt-4o"
    LITELLM_EMBEDDING_MODEL: str = "text-embedding-3-large"
    IMAGE_GEN_MODEL: str = "gemini/imagen-4.0-fast-generate-001"  # Image generation model via LiteLLM proxy
    RESEARCH_CACHE_TTL_MINUTES: int = 90
    RESEARCH_ARXIV_MAX_RETRIES: int = 3
    RESEARCH_ARXIV_BACKOFF_SECONDS: float = 1.0
    RESEARCH_ARXIV_MIN_REQUEST_INTERVAL_SECONDS: float = 3.5
    RESEARCH_ARXIV_TIMEOUT_SECONDS: float = 30.0
    RESEARCH_ARXIV_USER_AGENT: str = "amzur-research-digest/1.0 (mailto:support@example.com)"
    RESEARCH_MCP_SERVER_COMMAND: str = ""
    RESEARCH_MCP_SERVER_SCRIPT: str = str(BASE_DIR.parent / "mcp_server" / "server.py")
    RESEARCH_MCP_SERVER_CWD: str = str(BASE_DIR.parent)
    RESEARCH_MCP_TOOL_TIMEOUT_SECONDS: float = 45.0
    RESEARCH_MCP_LOG_LEVEL: str = "INFO"
    
    # Google Gemini
    GOOGLE_GEMINI_API_KEY: str = "AIzaSyD6rbz7oKzMMoTAyhcvbgmhcenJo9K2dw4"  # Set via environment variable (Get from https://aistudio.google.com/app/apikey)
    GEMINI_IMAGE_MODEL: str = "gemini-2.0-flash"  # Google Gemini 2.0 Flash model for images
    
    # Database - Supabase PostgreSQL
    DATABASE_URL: str = "postgresql://user:password@localhost:5432/chatbot_db"
    CHROMA_PERSIST_DIR: str = "./chroma_db"
    
    # JWT/Authentication
    SECRET_KEY: str = "your-secret-key-change-in-production"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 1440  # 24 hours
    
    # Google OAuth
    GOOGLE_CLIENT_ID: str = ""  # Set via environment variable
    GOOGLE_CLIENT_SECRET: str = ""  # Set via environment variable
    GOOGLE_SHEETS_API_KEY: str = ""  # Optional API key for Google Sheets API
    GOOGLE_SERVICE_ACCOUNT_FILE: str = ""  # Optional path to service account JSON (legacy key)
    GOOGLE_SERVICE_ACCOUNT_JSON: str = ""  # Full service account JSON string (preferred) or JSON key file path
    
    # CORS - Allow all common development ports
    ALLOWED_ORIGINS: list[str] = [
        "http://localhost:3000",
        "http://localhost:5173",
        "http://localhost:5174",
        "http://localhost:5175",
        "http://127.0.0.1:3000",
        "http://127.0.0.1:5173",
        "http://127.0.0.1:5174",
        "http://127.0.0.1:5175",
    ]


settings = Settings()
