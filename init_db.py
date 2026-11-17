"""
init_db.py - Automatic SQLite database initialization for the Secure Login System.

Creates database.db (next to this script) with the required `users` table:
    id, username, email, password_hash, otp_code, otp_expiry

Run manually with:   python init_db.py            (creates DB only)
                     python init_db.py --seed     (also adds a demo account)
The Flask app also calls init_db() automatically at startup.
"""

import os
import sqlite3

# Database lives beside this file so it works from any working directory.
DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "database.db")


def get_connection():
    """Return a SQLite connection with row access by column name."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db(seed_demo=False):
    """Create the users table if it does not exist and optionally seed a demo user."""
    conn = get_connection()
    cur = conn.cursor()

    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS users (
            id            INTEGER PRIMARY KEY AUTOINCREMENT,
            username      TEXT NOT NULL UNIQUE,
            email         TEXT NOT NULL UNIQUE,
            password_hash TEXT NOT NULL,
            otp_code      TEXT,
            otp_expiry    INTEGER,
            reset_code    TEXT,
            reset_expiry  INTEGER,
            created_at    TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """
    )
    conn.commit()

    # Migration for databases created by an older version of this script.
    cur.execute("PRAGMA table_info(users)")
    columns = {row["name"] for row in cur.fetchall()}
    if "reset_code" not in columns:
        cur.execute("ALTER TABLE users ADD COLUMN reset_code TEXT")
    if "reset_expiry" not in columns:
        cur.execute("ALTER TABLE users ADD COLUMN reset_expiry INTEGER")
    conn.commit()

    if seed_demo:
        from werkzeug.security import generate_password_hash

        cur.execute("SELECT id FROM users WHERE username = ?", ("demo",))
        if cur.fetchone() is None:
            cur.execute(
                "INSERT INTO users (username, email, password_hash) VALUES (?, ?, ?)",
                ("demo", "kanu6a6y@gmail.com", generate_password_hash("Demo@1234")),
            )
            conn.commit()
            print("[init_db] Demo account created -> username: demo | email: kanu6a6y@gmail.com | password: Demo@1234")

    conn.close()
    print("[init_db] SQLite database ready at: {}".format(DB_PATH))
    return DB_PATH


if __name__ == "__main__":
    import sys

    init_db(seed_demo="--seed" in sys.argv)
