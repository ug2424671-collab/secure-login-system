"""SQLite connection helpers and idempotent schema initialisation."""

from __future__ import annotations

import sqlite3
import time
from pathlib import Path

from flask import current_app, g
from werkzeug.security import generate_password_hash

SCHEMA = """
CREATE TABLE IF NOT EXISTS users (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    username        TEXT    NOT NULL UNIQUE COLLATE NOCASE,
    email           TEXT    NOT NULL UNIQUE COLLATE NOCASE,
    password_hash   TEXT    NOT NULL,
    otp_code        TEXT,
    otp_expiry      INTEGER,
    otp_attempts    INTEGER NOT NULL DEFAULT 0,
    otp_last_sent   INTEGER,
    reset_code      TEXT,
    reset_expiry    INTEGER,
    reset_attempts  INTEGER NOT NULL DEFAULT 0,
    reset_last_sent INTEGER,
    failed_logins   INTEGER NOT NULL DEFAULT 0,
    locked_until    INTEGER,
    created_at      INTEGER NOT NULL,
    last_login_at   INTEGER
);

CREATE INDEX IF NOT EXISTS idx_users_email  ON users(email COLLATE NOCASE);
CREATE INDEX IF NOT EXISTS idx_users_locked ON users(locked_until);
"""


def connect(database_path: str | Path) -> sqlite3.Connection:
    """Open a tuned SQLite connection with dictionary-like rows."""
    conn = sqlite3.connect(str(database_path), timeout=10)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    conn.execute("PRAGMA busy_timeout = 5000")
    return conn


def init_db(database_path: str | Path) -> Path:
    """Create the database file and users table if they do not exist."""
    path = Path(database_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with connect(path) as conn:
        conn.executescript(SCHEMA)
        conn.execute("PRAGMA user_version = 1")
    # Restrict permissions on the local database (best effort on POSIX).
    try:
        path.chmod(0o600)
    except OSError:
        pass
    return path


def seed_demo_account(
    database_path: str | Path,
    *,
    username: str = "demo",
    email: str = "",
    password: str = "Demo@1234",
) -> bool:
    """Create the ready-to-use demo account when it does not already exist.

    Returns ``True`` only when a new row was inserted. Existing accounts are
    never modified, so a password reset performed by the user is preserved.
    """
    username = (username or "").strip()
    email = (email or "").strip().lower()
    if not username or not email or not password:
        return False

    with connect(database_path) as conn:
        existing = conn.execute(
            "SELECT id FROM users WHERE username = ? COLLATE NOCASE",
            (username,),
        ).fetchone()
        if existing:
            return False

        # The demo email must also be unique. If another account already owns
        # it, leave the database untouched rather than risking a conflict.
        if conn.execute(
            "SELECT id FROM users WHERE email = ? COLLATE NOCASE", (email,)
        ).fetchone():
            return False

        conn.execute(
            """INSERT INTO users (username, email, password_hash, created_at)
               VALUES (?, ?, ?, ?)""",
            (
                username,
                email,
                generate_password_hash(password),
                int(time.time()),
            ),
        )
        return True


def get_db() -> sqlite3.Connection:
    """Return the request-scoped connection, creating it on first use."""
    if "db" not in g:
        g.db = connect(current_app.config["DATABASE_PATH"])
    return g.db


def close_db(_exception: BaseException | None = None) -> None:
    conn = g.pop("db", None)
    if conn is not None:
        conn.close()


def init_app(app) -> None:
    """Initialise the database at startup and close connections per request."""
    init_db(app.config["DATABASE_PATH"])
    app.teardown_appcontext(close_db)
