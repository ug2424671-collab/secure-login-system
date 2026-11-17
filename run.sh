#!/usr/bin/env bash
# Secure Login System - one-command local launcher.
set -euo pipefail

cd "$(dirname "$0")"

if [ ! -x ".venv/bin/python" ]; then
  echo "Creating virtual environment..."
  python3 -m venv .venv
fi

if ! .venv/bin/python -c "import flask, dotenv, fpdf" >/dev/null 2>&1; then
  echo "Installing dependencies..."
  .venv/bin/python -m pip install -q -r requirements.txt
fi

if [ ! -f ".env" ]; then
  echo "Creating .env from template and generating a secret key..."
  cp .env.example .env
  SECRET="$(.venv/bin/python -c 'import secrets; print(secrets.token_hex(32))')"
  .venv/bin/python - "$SECRET" <<'PY'
import pathlib
import sys

path = pathlib.Path(".env")
text = path.read_text()
text = text.replace("SECRET_KEY=replace-with-a-long-random-value", f"SECRET_KEY={sys.argv[1]}")
path.write_text(text)
path.chmod(0o600)
PY
  echo "Edit .env to set MAIL_USERNAME, MAIL_PASSWORD and OTP_RECIPIENT_OVERRIDE."
fi

.venv/bin/python init_db.py
exec .venv/bin/python app.py
