"""Application configuration.

Secrets are read from environment variables (loaded from .env in development).
Nothing sensitive is hard-coded here.
"""
import os
from pathlib import Path
from dotenv import load_dotenv

# Project root = folder that contains run.py
basedir = Path(__file__).resolve().parent.parent
load_dotenv(basedir / ".env")


def _database_url() -> str:
    url = os.environ.get("DATABASE_URL")
    if not url:
        # Default local database
        return f"sqlite:///{basedir / 'platform.db'}"
    # Render/Heroku give "postgres://" but SQLAlchemy needs "postgresql://"
    if url.startswith("postgres://"):
        url = url.replace("postgres://", "postgresql://", 1)
    return url


class Config:
    SECRET_KEY = os.environ.get("SECRET_KEY", "dev-only-insecure-key")
    SQLALCHEMY_DATABASE_URI = _database_url()
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    WTF_CSRF_ENABLED = True

    # When True, the GoPhish layer uses synthetic demo events (no real email).
    DEMO_MODE = os.environ.get("DEMO_MODE", "true").lower() == "true"

    # Limit uploaded file size (CSV import) to 2 MB.
    MAX_CONTENT_LENGTH = 2 * 1024 * 1024

    # Integrations (used in later stages)
    GOPHISH_API_URL = os.environ.get("GOPHISH_API_URL", "")
    GOPHISH_API_KEY = os.environ.get("GOPHISH_API_KEY", "")
    # GoPhish admin uses a self-signed certificate in most lab setups.
    GOPHISH_VERIFY_SSL = os.environ.get("GOPHISH_VERIFY_SSL", "false").lower() == "true"

    # Mailtrap SMTP sandbox for safe test emails (Stage 5)
    MAILTRAP_HOST = os.environ.get("MAILTRAP_HOST", "sandbox.smtp.mailtrap.io")
    MAILTRAP_PORT = int(os.environ.get("MAILTRAP_PORT", "2525"))
    MAILTRAP_USERNAME = os.environ.get("MAILTRAP_USERNAME", "")
    MAILTRAP_PASSWORD = os.environ.get("MAILTRAP_PASSWORD", "")


class DevelopmentConfig(Config):
    DEBUG = True


class ProductionConfig(Config):
    DEBUG = False
    # Secure cookies in production
    SESSION_COOKIE_SECURE = True
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = "Lax"


config_by_name = {
    "development": DevelopmentConfig,
    "production": ProductionConfig,
}
