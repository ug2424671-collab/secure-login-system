"""
env_utils.py - tiny .env loader (no external dependency).

Reads KEY=VALUE lines from a local .env file into os.environ without
overwriting variables that are already set in the shell. This lets the project
keep SMTP credentials out of the source code and out of version control.
"""

import os


def load_env_file(path=None):
    """Load .env beside this file. Returns True when the file was read."""
    if path is None:
        path = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env")
    if not os.path.exists(path):
        return False

    try:
        with open(path, "r", encoding="utf-8") as handle:
            for raw in handle:
                line = raw.strip()
                if not line or line.startswith("#") or "=" not in line:
                    continue
                key, value = line.split("=", 1)
                key = key.strip()
                value = value.strip().strip('"').strip("'")
                if key:
                    os.environ.setdefault(key, value)
    except OSError:
        return False
    return True
