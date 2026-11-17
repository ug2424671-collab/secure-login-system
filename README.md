# Secure Login System (Flask + SQLite)

A complete, ready-to-run web application demonstrating **Two-Step Verification (2FA)**
and **password hashing** with a local SQLite database.

## Project Structure

```
secure_login_system/
|-- app.py                 # Flask application (all routes & security logic)
|-- init_db.py             # Automatic database initialization
|-- generate_report.py     # Generates Assignment_Report.pdf
|-- database.db            # SQLite database (created automatically)
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

### Optional: receive the OTP by email
SMTP is optional and reads credentials only from environment variables (never from
source code). To email the code to the address on the account:

1. In your Google Account go to **Security -> 2-Step Verification -> App passwords**
   and generate an app password for Mail.
2. Put the credentials in the local `.env` file (loaded automatically, ignored by git):
   ```bash
   # edit .env
   GMAIL_ADDRESS=kanu6a6y@gmail.com
   GMAIL_APP_PASSWORD=your-16-character-app-password
   ```
   Alternatively, export them in the terminal that starts the server.
3. Verify the configuration, then restart the server:
   ```bash
   python test_email.py
   python app.py
   ```
   The OTP will now also be emailed to the login address; the terminal and testing
   banner keep working as a fallback.

### Not receiving emails?
Run the diagnostic and read its output:
```bash
cd /home/pc/secure_login_system
source venv/bin/activate
python test_email.py
```
- `SMTP is NOT configured` means neither `.env` nor the environment contains the two
  values. Fill in `.env` and restart the server.
- `FAILED: ...` usually means a normal Google password was used. Gmail requires a
  16-character **App Password**, and 2-Step Verification must be enabled on the
  Google account first.
- Environment variables set in one terminal are not visible to a server started in
  another terminal - stop and restart `python app.py` in the same terminal.

Either way, the OTP is always shown in the server terminal and on the `/verify-2fa`
page, so the demo never gets blocked by email problems.

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
