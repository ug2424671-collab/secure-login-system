"""
mailer.py - SMTP email helper.

Works with Gmail (default) or any SMTP provider, including free test inboxes
such as Ethereal. Credentials come from environment variables / .env only.

Supported environment variables:
    SMTP_HOST    SMTP server host           (default smtp.gmail.com)
    SMTP_PORT    SMTP server port           (default 465)
    SMTP_SECURE  ssl | starttls | none      (default ssl)
    SMTP_USER    SMTP username / email
    SMTP_PASS    SMTP password / app password
    SMTP_FROM    From address               (default SMTP_USER)

GMAIL_ADDRESS / GMAIL_APP_PASSWORD are still honoured as fallbacks.
"""

import os
import smtplib
from email.message import EmailMessage

from env_utils import load_env_file

load_env_file()


def _as_int(value, default):
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


SMTP_HOST = os.environ.get("SMTP_HOST", "smtp.gmail.com").strip()
SMTP_PORT = _as_int(os.environ.get("SMTP_PORT"), 465)
SMTP_SECURE = os.environ.get("SMTP_SECURE", "ssl").strip().lower()
SMTP_USER = (os.environ.get("SMTP_USER") or os.environ.get("GMAIL_ADDRESS", "")).strip()
SMTP_PASS = os.environ.get("SMTP_PASS") or os.environ.get("GMAIL_APP_PASSWORD", "")
SMTP_FROM = (os.environ.get("SMTP_FROM") or SMTP_USER).strip()


def is_configured():
    """True when a host and credentials are available."""
    return bool(SMTP_HOST and SMTP_USER and SMTP_PASS)


def config_summary():
    """Safe-to-display configuration (never includes the password)."""
    return {
        "host": SMTP_HOST,
        "port": SMTP_PORT,
        "secure": SMTP_SECURE,
        "user": SMTP_USER,
        "sender": SMTP_FROM,
        "password": "set ({} chars)".format(len(SMTP_PASS)) if SMTP_PASS else "<not set>",
    }


def send_email(to_email, subject, body):
    """Send one plain-text email. Returns (ok, detail)."""
    if not is_configured():
        return False, "SMTP is not configured (SMTP_HOST / SMTP_USER / SMTP_PASS)."

    message = EmailMessage()
    message["Subject"] = subject
    message["From"] = SMTP_FROM
    message["To"] = to_email
    message.set_content(body)

    try:
        if SMTP_SECURE == "ssl":
            smtp = smtplib.SMTP_SSL(SMTP_HOST, SMTP_PORT, timeout=20)
        else:
            smtp = smtplib.SMTP(SMTP_HOST, SMTP_PORT, timeout=20)

        with smtp:
            smtp.ehlo()
            if SMTP_SECURE == "starttls":
                smtp.starttls()
                smtp.ehlo()
            if SMTP_USER and SMTP_PASS:
                smtp.login(SMTP_USER, SMTP_PASS)
            smtp.send_message(message)
        return True, "sent"
    except Exception as exc:
        return False, str(exc)
