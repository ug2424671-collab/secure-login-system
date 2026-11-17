"""Application configuration loaded from environment variables / .env."""

from __future__ import annotations

import os
import secrets
from datetime import timedelta
from pathlib import Path

from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent
load_dotenv(BASE_DIR / ".env")


def _as_bool(value: str | None, default: bool = False) -> bool:
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


class Config:
    """Flask configuration with safe local-development defaults."""

    # Core
    SECRET_KEY = os.getenv("SECRET_KEY") or secrets.token_hex(32)
    DATABASE_PATH = str(
        (BASE_DIR / os.getenv("DATABASE_PATH", "database.db")).resolve()
    )
    APP_ENV = os.getenv("APP_ENV", "development").strip().lower()
    DEMO_MODE = _as_bool(os.getenv("DEMO_MODE"), default=True)
    DEMO_SHOW_OTP = _as_bool(os.getenv("DEMO_SHOW_OTP"), default=DEMO_MODE)
    DEMO_ACCOUNT_USERNAME = os.getenv("DEMO_ACCOUNT_USERNAME", "demo").strip() or "demo"
    DEMO_ACCOUNT_PASSWORD = os.getenv("DEMO_ACCOUNT_PASSWORD", "Demo@1234")
    HOST = os.getenv("HOST", "127.0.0.1")
    PORT = int(os.getenv("PORT", "5055"))

    # Cookie / session hardening (secure=False only because local HTTP is used)
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = "Lax"
    SESSION_COOKIE_SECURE = _as_bool(os.getenv("SESSION_COOKIE_SECURE"), default=False)
    PERMANENT_SESSION_LIFETIME = timedelta(hours=2)
    MAX_CONTENT_LENGTH = 1 * 1024 * 1024  # 1 MB request bodies

    # One-time passwords
    OTP_TTL_SECONDS = int(os.getenv("OTP_TTL_SECONDS", "300"))  # 5 minutes
    OTP_RESEND_SECONDS = int(os.getenv("OTP_RESEND_SECONDS", "60"))
    OTP_MAX_ATTEMPTS = int(os.getenv("OTP_MAX_ATTEMPTS", "5"))
    OTP_PENDING_TTL_SECONDS = int(os.getenv("OTP_PENDING_TTL_SECONDS", "900"))
    RESET_TTL_SECONDS = int(os.getenv("RESET_TTL_SECONDS", "600"))  # 10 minutes
    RESET_MAX_ATTEMPTS = int(os.getenv("RESET_MAX_ATTEMPTS", "5"))

    # Login lockout
    LOGIN_MAX_FAILURES = int(os.getenv("LOGIN_MAX_FAILURES", "5"))
    LOGIN_LOCK_SECONDS = int(os.getenv("LOGIN_LOCK_SECONDS", "300"))

    # SMTP delivery. All codes are forced to OTP_RECIPIENT_OVERRIDE when set.
    MAIL_SERVER = os.getenv("MAIL_SERVER", "smtp.gmail.com")
    MAIL_PORT = int(os.getenv("MAIL_PORT", "465"))
    MAIL_USE_SSL = _as_bool(os.getenv("MAIL_USE_SSL"), default=True)
    MAIL_USERNAME = os.getenv("MAIL_USERNAME", "").strip()
    MAIL_PASSWORD = os.getenv("MAIL_PASSWORD", "")
    MAIL_FROM_NAME = os.getenv("MAIL_FROM_NAME", "Secure Login System")
    MAIL_TIMEOUT = int(os.getenv("MAIL_TIMEOUT", "12"))
    OTP_RECIPIENT_OVERRIDE = os.getenv("OTP_RECIPIENT_OVERRIDE", "").strip().lower()
