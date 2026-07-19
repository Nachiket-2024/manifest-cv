from pydantic import field_validator
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application configuration, loaded from environment variables / .env."""

    BACKEND_BASE_URL: str                           # Backend URL for Auth redirection from frontend
    FRONTEND_BASE_URL: str                          # Frontend URL for redirection

    DATABASE_URL: str                               # Async PostgreSQL connection URL
    POSTGRES_USER: str                              # PostgreSQL username
    POSTGRES_PASSWORD: str                          # PostgreSQL password
    POSTGRES_DB: str                                # PostgreSQL DB name

    SECRET_KEY: str                                 # Secret key for JWT encoding
    ACCESS_TOKEN_EXPIRE_MINUTES: int                # Access token expiration time in minutes
    REFRESH_TOKEN_EXPIRE_MINUTES: int               # Refresh token expiration time in minutes
    JWT_ALGORITHM: str                              # Algorithm for JWT encoding
    RESET_TOKEN_EXPIRE_MINUTES: int                 # Password reset token expiration time in minutes

    GOOGLE_CLIENT_ID: str                           # OAuth2 Client ID for Gmail
    GOOGLE_CLIENT_SECRET: str                       # OAuth2 Client Secret for Gmail
    GOOGLE_REDIRECT_URI: str                        # OAuth2 redirect URI for Gmail login

    REDIS_URL: str                                  # Redis connection URL
    CACHE_DEFAULT_TTL: int                          # Default TTL for Redis cache keys in seconds

    FROM_EMAIL: str                                 # Email address used to send password reset emails
    GMAIL_APP_PASSWORD: str                         # Gmail App password for sending email from above account
    SUPPORT_EMAIL: str = ""                         # Reply-to/contact address shown in email footers (defaults to FROM_EMAIL if unset)

    SMTP_HOST: str = "smtp.gmail.com"               # SMTP server host (defaulted to Gmail so existing .env files keep working; override to point emails/email_sender.py at another provider)
    SMTP_PORT: int = 587                            # SMTP server port (587 = STARTTLS, Gmail's default)

    APP_NAME: str                                    # Product name shown in email branding and API responses

    LOGIN_LOCKOUT_TIME: int                         # Time in seconds to lockout after failed login attempts
    MAX_FAILED_LOGIN_ATTEMPTS: int                  # Max failed login attempts before lockout
    LOGIN_LOCKOUT_TIME_PER_IP: int                  # Time in seconds to lock out an IP after too many failed logins across accounts
    MAX_FAILED_LOGIN_ATTEMPTS_PER_IP: int           # Max failed login attempts from a single IP (across any accounts) before that IP is locked out
    MAX_REQUESTS_PER_WINDOW: int                    # Max requests allowed per rate limit window
    REQUEST_WINDOW_SECONDS: int                     # Time window for rate limiting in seconds

    LOG_LEVEL: str = "INFO"                         # Application log level (defaulted so existing .env files/CI keep working)
    LOG_DIR: str = "logs"                           # Directory for file-based logs; relative paths resolve against the backend package root. Override for environments where that default isn't writable.

    ENVIRONMENT: str = "development"                # "development" or "production" (defaulted so existing .env files/CI keep working) — gates docs/redoc exposure in main.py

    TRUSTED_PROXY_IPS: str = ""                     # Comma-separated reverse proxy IPs to trust X-Forwarded-For from (see auth/security/client_ip.py). Empty (default) = never trust it, use request.client.host as-is.

    # ManifestCV — AI structuring (Gemini) + vector retrieval (Qdrant). Owned by
    # ai_integration/ and retrieval/, never read by mystic-auth-owned code.
    GEMINI_API_KEY: str                             # API key for Google's Gemini API (https://aistudio.google.com/apikey)
    GEMINI_MODEL: str = "gemini-flash-latest"        # Text generation model used to structure raw career input into Markdown (self-updating alias, avoids pinning to a version Google later deprecates)
    GEMINI_EMBEDDING_MODEL: str = "gemini-embedding-001"  # Embedding model used for semantic search over knowledge base content
    QDRANT_URL: str = "http://qdrant:6333"           # Self-hosted Qdrant HTTP API (Docker service hostname; swap to localhost when running outside Docker)

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"

    @field_validator("SECRET_KEY")
    @classmethod
    def _secret_key_minimum_strength(cls, value: str) -> str:
        # A short/low-entropy SECRET_KEY would otherwise go undetected until
        # someone forges a token against it — fail fast at startup instead.
        # 32 chars is a floor, not a real entropy guarantee; it only catches
        # placeholder/example values like "changeme" or "secret".
        if len(value) < 32:
            raise ValueError("SECRET_KEY must be at least 32 characters long")
        return value


settings = Settings()
