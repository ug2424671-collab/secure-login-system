# Secure Login System (Flask + SQLite)

A complete, ready-to-run web application demonstrating **Two-Step Verification (2FA)**
and **password hashing** with a local SQLite database.

## Project Structure

```
secure_login_system/
|-- app.py                 # Flask application (all routes & security logic)
|-- init_db.py             # Automatic database initialization
|-- env_utils.py           # Tiny .env loader (no extra dependency)
|-- mailer.py              # SMTP email helper (Gmail or any provider)
|-- test_email.py          # SMTP diagnostic / test message
|-- generate_report.py     # Generates Assignment_Report.pdf
|-- database.db            # SQLite database (created automatically)
|-- .env.example           # Example email configuration
|-- requirements.txt
|-- templates/
|   |-- base.html
|   |-- register.html
|   |-- login.html
|   |-- verify_2fa.html
|   `-- dashboard.html
|-- static/
|   `-- style.css
`-- Assignment_Report.pdf  # Generated after running generate_report.py
```

## Quick Start

```bash
cd /home/pc/secure_login_system
source venv/bin/activate
python app.py
```

Open **http://127.0.0.1:5000** in a browser.

Demo account (seeded automatically on first run):

- Email: `kanu6a6y@gmail.com` (or username `demo`)
- Password: `Demo@1234`

OTP delivery is controlled by `OTP_DELIVERY` in `.env`:

- `OTP_DELIVERY=email` (current default) - the code is emailed to the account
  address and is **never** printed in the terminal or shown on screen. Requires
  the Gmail App Password below; login is blocked with a clear message until it is set.
- `OTP_DELIVERY=demo` - the code is printed in the terminal and shown in the
  yellow testing banner, so no email service is needed.

To use the demo mode instantly, change `.env` to `OTP_DELIVERY=demo` and restart.

### Email delivery (email-only by default)
The app works with any SMTP provider. Credentials live only in `.env` (ignored by
git). `OTP_DELIVERY=email` sends the code to the account address and never shows it
on screen; `OTP_DELIVERY=demo` is the offline fallback.

**Gmail** (real delivery to your phone) - create a 16-character App Password at
Google Account -> Security -> 2-Step Verification -> App passwords, then set:

```env
SMTP_HOST=smtp.gmail.com
SMTP_PORT=465
SMTP_SECURE=ssl
SMTP_USER=kanu6a6y@gmail.com
SMTP_PASS=your-16-character-app-password
SMTP_FROM=kanu6a6y@gmail.com
OTP_DELIVERY=email
```

**Ethereal** (free test inbox, no personal credentials; view at https://ethereal.email):

```env
SMTP_HOST=smtp.ethereal.email
SMTP_PORT=587
SMTP_SECURE=starttls
SMTP_USER=your-user@ethereal.email
SMTP_PASS=your-ethereal-password
SMTP_FROM=your-user@ethereal.email
OTP_DELIVERY=email
```

Verify and restart:

```bash
python test_email.py
python app.py
```

### Not receiving emails?
Run the diagnostic and read its output:
```bash
cd /home/pc/secure_login_system
source venv/bin/activate
python test_email.py
```
- `SMTP is NOT configured` means `SMTP_HOST`, `SMTP_USER` or `SMTP_PASS` is missing
  from `.env` / the environment. Fill it in and restart the server.
- `FAILED: ...` with Gmail usually means a normal Google password was used. Gmail
  requires a 16-character **App Password**, with 2-Step Verification enabled.
- For port 587 set `SMTP_SECURE=starttls`; for port 465 use `SMTP_SECURE=ssl`.
- Because the app reads `.env` at startup, restart `python app.py` after changing it.

In email-only mode nothing is shown on screen: login is blocked until SMTP works,
which is intentional. Use `OTP_DELIVERY=demo` only for offline demonstrations.

## Forgot Password

Open `/forgot-password`, enter the account email, and a 6-digit reset code is
generated (valid 15 minutes), printed to the terminal, shown in a testing banner,
and emailed when SMTP is configured. The new password is hashed with Werkzeug
before being stored, and the reset code is deleted after use or expiry.

## Routes

| Route | Purpose |
|-------|---------|
| `/register` | Create an account (password is hashed before storage) |
| `/login` | Verify credentials, generate and store OTP, redirect to 2FA |
| `/verify-2fa` | Verify the 6-digit OTP and start an authenticated session |
| `/resend-otp` | Generate a fresh login OTP |
| `/forgot-password` | Request a password reset code by email |
| `/reset-password` | Enter the reset code and choose a new password |
| `/resend-reset` | Generate a fresh reset code |
| `/dashboard` | Protected page (requires completed 2FA) |
| `/logout` | Clear the session |

## Generate the PDF Report

```bash
python generate_report.py
```

This writes `Assignment_Report.pdf` in the project root.

## Database

`init_db.py` creates `database.db` with the `users` table:
`id`, `username`, `email`, `password_hash`, `otp_code`, `otp_expiry`
(plus `created_at`). Re-running it is safe thanks to `CREATE TABLE IF NOT EXISTS`.
