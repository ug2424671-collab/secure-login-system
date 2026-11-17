#!/usr/bin/env python3
"""Initialise the local SQLite database.

Usage:
    python init_db.py            # create database.db / users table if missing
    python init_db.py --reset    # DESTRUCTIVE: delete all data and recreate
    python init_db.py --show     # print schema and row count
"""

from __future__ import annotations

import argparse
import sqlite3
import sys
from pathlib import Path

from config import Config
from db import connect, init_db


def show_database(path: Path) -> None:
    with connect(path) as conn:
        tables = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"
        ).fetchall()
        print(f"Database : {path}")
        print(f"Tables   : {', '.join(row['name'] for row in tables)}")
        try:
            count = conn.execute("SELECT COUNT(*) AS n FROM users").fetchone()["n"]
            print(f"Users    : {count}")
        except sqlite3.Error:
            print("Users    : table not initialised")
        print("\nSchema:")
        row = conn.execute(
            "SELECT sql FROM sqlite_master WHERE type='table' AND name='users'"
        ).fetchone()
        print(row["sql"] if row else "(users table missing)")


def main() -> int:
    parser = argparse.ArgumentParser(description="Create the Secure Login database.")
    parser.add_argument(
        "--reset",
        action="store_true",
        help="delete the existing database before creating a fresh one",
    )
    parser.add_argument(
        "--show", action="store_true", help="show the schema and a user count"
    )
    parser.add_argument(
        "--seed",
        action="store_true",
        help="create the demo login if it does not already exist",
    )
    args = parser.parse_args()

    path = Path(Config.DATABASE_PATH)
    if args.reset and path.exists():
        path.unlink()
        print(f"Removed existing database: {path}")

    init_db(path)
    print(f"Database ready: {path}")
    if args.seed or args.reset:
        from db import seed_demo_account

        created = seed_demo_account(
            path,
            username=Config.DEMO_ACCOUNT_USERNAME,
            email=Config.OTP_RECIPIENT_OVERRIDE or "demo@example.com",
            password=Config.DEMO_ACCOUNT_PASSWORD,
        )
        print(
            "Demo login created: "
            f"{Config.DEMO_ACCOUNT_USERNAME} / {Config.DEMO_ACCOUNT_PASSWORD}"
            if created
            else "Demo login already exists (unchanged)."
        )
    if args.show:
        print()
        show_database(path)
    return 0


if __name__ == "__main__":
    sys.exit(main())
