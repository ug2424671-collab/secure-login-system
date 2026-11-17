"""Secure Login System - Flask application.

Features: registration, password hashing, 2-step verification (email OTP),
a protected dashboard, login lockout and forgot/reset password.
"""

from __future__ import annotations

import hmac
import math
import os
import re
import secrets
import sqlite3
import time
from datetime import datetime, timezone
from functools import wraps
from hashlib import sha256

from flask import (
    Flask,
    abort,
    flash,
    redirect,
    render_template,
    request,
    session,
    url_for,
)
from werkzeug.security import check_password_hash, generate_password_hash

import db
from config import Config
from mailer import send_otp_email

app = Flask(__name__)
app.config.from_object(Config)
db.init_app(app)

EMAIL_RE = re.compile(r"^[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}$")
USERNAME_RE = re.compile(r"^[A-Za-z0-9_.\-]{3,32}$")

# Checking this hash for unknown accounts keeps invalid-login timing consistent.
DUMMY_HASH = generate_password_hash("not-a-real-password")


# ---------------------------------------------------------------------------
# Small security helpers
# ---------------------------------------------------------------------------
def utc_now() -> int:
    return int(time.time())


def normalize_email(value: str | None) -> str:
    return (value or "").strip().lower()


def password_policy_errors(password: str) -> list[str]:
    errors = []
    if len(password) < 10:
        errors.append("at least 10 characters")
    if not re.search(r"[a-z]", password):
        errors.append("a lowercase letter")
    if not re.search(r"[A-Z]", password):
        errors.append("an uppercase letter")
    if not re.search(r"\d", password):
        errors.append("a number")
    if not re.search(r"[^A-Za-z0-9]", password):
        errors.append("a special character")
    return errors


def hash_otp(code: str) -> str:
    """Keyed hash so a leaked database does not expose live OTPs."""
    key = app.config["SECRET_KEY"].encode("utf-8")
    return hmac.new(key, code.encode("utf-8"), sha256).hexdigest()


def otp_matches(code: str, stored_hash: str | None) -> bool:
    if not stored_hash:
        return False
    return hmac.compare_digest(hash_otp(code), stored_hash)


def mask_email(address: str) -> str:
    try:
        local, domain = address.split("@", 1)
    except ValueError:
        return "configured inbox"
    if len(local) <= 2:
        masked = local[:1] + "***"
    else:
        masked = f"{local[0]}{'*' * (len(local) - 2)}{local[-1]}"
    return f"{masked}@{domain}"


def owner_inbox() -> str:
    return app.config.get("OTP_RECIPIENT_OVERRIDE") or app.config.get(
        "MAIL_USERNAME", ""
    )


def get_csrf_token() -> str:
    token = session.get("_csrf_token")
    if not token:
        token = secrets.token_urlsafe(32)
        session["_csrf_token"] = token
    return token


def login_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        if not session.get("user_id"):
            flash("Please sign in to access your dashboard.", "warning")
            return redirect(url_for("login"))
        return view(*args, **kwargs)

    return wrapped


def manual_delivery(code: str, user: sqlite3.Row, purpose: str, recipient: str) -> None:
    label = "2FA LOGIN CODE" if purpose == "login" else "PASSWORD RESET CODE"
    ttl = (
        app.config["RESET_TTL_SECONDS"]
        if purpose == "password_reset"
        else app.config["OTP_TTL_SECONDS"]
    )
    print("\n" + "=" * 66, flush=True)
    print(f"  {label} - SECURE LOGIN SYSTEM", flush=True)
    print("-" * 66, flush=True)
    print(f"  Account : {user['username']} ({user['email']})", flush=True)
    print(f"  Code    : {code}", flush=True)
    print(f"  Target  : {recipient} (authorised owner inbox)", flush=True)
    print(f"  Expires : {ttl // 60} minutes", flush=True)
    print("=" * 66 + "\n", flush=True)


def clear_demo_code() -> None:
    for key in (
        "demo_code",
        "demo_code_purpose",
        "demo_code_user_id",
        "demo_code_expires",
    ):
        session.pop(key, None)


def remember_demo_code(
    user: sqlite3.Row, code: str, purpose: str, sent: bool
) -> None:
    """Keep the plaintext code in the signed session for on-screen demo use.

    The database continues to store only the HMAC digest. A code is displayed
    only when demo display is enabled and SMTP delivery was not successful.
    """
    if sent or not app.config.get("DEMO_SHOW_OTP"):
        clear_demo_code()
        return

    ttl = (
        app.config["RESET_TTL_SECONDS"]
        if purpose == "password_reset"
        else app.config["OTP_TTL_SECONDS"]
    )
    session["demo_code"] = code
    session["demo_code_purpose"] = purpose
    session["demo_code_user_id"] = int(user["id"])
    session["demo_code_expires"] = utc_now() + ttl


def demo_code_for(purpose: str, user_id: int | None) -> str | None:
    if not app.config.get("DEMO_SHOW_OTP") or not user_id:
        return None
    if session.get("demo_code_purpose") != purpose:
        return None
    if session.get("demo_code_user_id") != int(user_id):
        return None
    if int(session.get("demo_code_expires") or 0) <= utc_now():
        clear_demo_code()
        return None
    return session.get("demo_code")


def deliver_code(user: sqlite3.Row, code: str, purpose: str) -> tuple[bool, str]:
    """Email the OTP to the fixed owner inbox and always print it locally."""
    owner = owner_inbox()
    ttl = (
        app.config["RESET_TTL_SECONDS"]
        if purpose == "password_reset"
        else app.config["OTP_TTL_SECONDS"]
    )
    sent, message, recipient = send_otp_email(
        to_email=owner or user["email"],
        code=code,
        purpose=purpose,
        username=user["username"],
        account_email=user["email"],
        ttl_minutes=max(1, ttl // 60),
    )
    manual_delivery(code, user, purpose, recipient)
    remember_demo_code(user, code, purpose, sent)

    if not sent and app.config.get("DEMO_SHOW_OTP"):
        message = (
            "Email delivery failed, so the code is shown on this page and "
            "printed in the server terminal."
        )
    return sent, message


def clear_pending_login() -> None:
    for key in ("pending_user_id", "pending_username", "pending_started"):
        session.pop(key, None)
    clear_demo_code()


def clear_pending_reset() -> None:
    for key in ("pending_reset_user_id", "pending_reset_started"):
        session.pop(key, None)
    clear_demo_code()


def fetch_user(user_id: int | None) -> sqlite3.Row | None:
    if not user_id:
        return None
    return (
        db.get_db()
        .execute("SELECT * FROM users WHERE id = ?", (user_id,))
        .fetchone()
    )


# ---------------------------------------------------------------------------
# Request hooks: CSRF, security headers, template globals
# ---------------------------------------------------------------------------
@app.before_request
def protect_post_requests():
    if request.method == "POST":
        token = request.form.get("csrf_token", "")
        expected = session.get("_csrf_token", "")
        if not expected or not hmac.compare_digest(token, expected):
            abort(400, description="Invalid or missing CSRF token. Reload the page.")


@app.after_request
def add_security_headers(response):
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    response.headers["Permissions-Policy"] = "camera=(), microphone=(), geolocation=()"
    response.headers["Content-Security-Policy"] = (
        "default-src 'self'; "
        "style-src 'self'; "
        "script-src 'self'; "
        "img-src 'self' data:; "
        "font-src 'self'; "
        "form-action 'self'; "
        "frame-ancestors 'none'; "
        "base-uri 'self'"
    )
    if response.mimetype == "text/html":
        response.headers["Cache-Control"] = "no-store, max-age=0"
    return response


@app.context_processor
def inject_globals():
    return {
        "csrf_token": get_csrf_token,
        "current_year": datetime.now(timezone.utc).year,
        "owner_masked": mask_email(owner_inbox()) if owner_inbox() else "your inbox",
        "demo_mode": app.config["DEMO_MODE"],
        "session_user": session.get("user_id"),
    }


# ---------------------------------------------------------------------------
# Public + authentication routes
# ---------------------------------------------------------------------------
@app.get("/")
def index():
    return redirect(url_for("dashboard") if session.get("user_id") else url_for("login"))


@app.get("/healthz")
def healthz():
    db.get_db().execute("SELECT 1").fetchone()
    return {"status": "ok", "database": "connected"}


@app.route("/register", methods=["GET", "POST"])
def register():
    if session.get("user_id"):
        return redirect(url_for("dashboard"))

    values = {"username": "", "email": ""}
    if request.method == "POST":
        username = (request.form.get("username") or "").strip()
        email = normalize_email(request.form.get("email"))
        password = request.form.get("password") or ""
        confirm = request.form.get("confirm_password") or ""
        values = {"username": username, "email": email}

        errors = []
        if not USERNAME_RE.fullmatch(username):
            errors.append(
                "Username must be 3-32 characters using letters, numbers, dots, dashes or underscores."
            )
        if not EMAIL_RE.fullmatch(email) or len(email) > 254:
            errors.append("Enter a valid email address.")
        policy = password_policy_errors(password)
        if policy:
            errors.append("Password must contain " + ", ".join(policy) + ".")
        if password != confirm:
            errors.append("Passwords do not match.")

        if not errors:
            try:
                with db.get_db() as conn:
                    conn.execute(
                        """INSERT INTO users
                           (username, email, password_hash, created_at)
                           VALUES (?, ?, ?, ?)""",
                        (
                            username,
                            email,
                            generate_password_hash(password),
                            utc_now(),
                        ),
                    )
            except sqlite3.IntegrityError:
                errors.append("That username or email is already registered.")
            else:
                flash(
                    "Account created successfully. Sign in to receive your 2FA code.",
                    "success",
                )
                return redirect(url_for("login"))

        for error in errors:
            flash(error, "error")

    return render_template("register.html", values=values)


@app.route("/login", methods=["GET", "POST"])
def login():
    if session.get("user_id"):
        return redirect(url_for("dashboard"))

    identifier = ""
    if request.method == "POST":
        identifier = (request.form.get("identifier") or "").strip()
        password = request.form.get("password") or ""
        user = (
            db.get_db()
            .execute(
                """SELECT * FROM users
                   WHERE email = ? COLLATE NOCASE
                      OR username = ? COLLATE NOCASE
                   LIMIT 1""",
                (identifier, identifier),
            )
            .fetchone()
        )

        now = utc_now()
        if user and user["locked_until"] and user["locked_until"] > now:
            wait_minutes = max(1, math.ceil((user["locked_until"] - now) / 60))
            flash(
                f"Too many failed attempts. Try again in {wait_minutes} minute(s).",
                "error",
            )
            return render_template("login.html", identifier=identifier), 429

        password_ok = (
            check_password_hash(user["password_hash"], password)
            if user
            else check_password_hash(DUMMY_HASH, password)
        )

        if not user or not password_ok:
            if user:
                failures = (user["failed_logins"] or 0) + 1
                locked_until = None
                if failures >= app.config["LOGIN_MAX_FAILURES"]:
                    locked_until = now + app.config["LOGIN_LOCK_SECONDS"]
                    failures = 0
                with db.get_db() as conn:
                    conn.execute(
                        "UPDATE users SET failed_logins = ?, locked_until = ? WHERE id = ?",
                        (failures, locked_until, user["id"]),
                    )
                if locked_until:
                    flash(
                        "Too many failed attempts. Your account is locked for "
                        f"{app.config['LOGIN_LOCK_SECONDS'] // 60} minutes.",
                        "error",
                    )
                    return render_template("login.html", identifier=identifier), 429
            flash("Invalid username/email or password.", "error")
        else:
            code = f"{secrets.randbelow(1_000_000):06d}"
            with db.get_db() as conn:
                conn.execute(
                    """UPDATE users
                       SET failed_logins = 0, locked_until = NULL,
                           otp_code = ?, otp_expiry = ?, otp_attempts = 0,
                           otp_last_sent = ?
                       WHERE id = ?""",
                    (
                        hash_otp(code),
                        now + app.config["OTP_TTL_SECONDS"],
                        now,
                        user["id"],
                    ),
                )

            # Rotate the session identifier data to prevent fixation.
            session.clear()
            session.permanent = True
            session["pending_user_id"] = user["id"]
            session["pending_username"] = user["username"]
            session["pending_started"] = now

            sent, message = deliver_code(user, code, "login")
            flash(message, "success" if sent else "warning")
            return redirect(url_for("verify_2fa"))

    return render_template("login.html", identifier=identifier)


@app.route("/verify-2fa", methods=["GET", "POST"])
def verify_2fa():
    user = fetch_user(session.get("pending_user_id"))
    if not user:
        clear_pending_login()
        flash("Your sign-in session expired. Please sign in again.", "warning")
        return redirect(url_for("login"))

    now = utc_now()
    if now - int(session.get("pending_started", 0)) > app.config["OTP_PENDING_TTL_SECONDS"]:
        with db.get_db() as conn:
            conn.execute(
                """UPDATE users SET otp_code = NULL, otp_expiry = NULL,
                                    otp_attempts = 0 WHERE id = ?""",
                (user["id"],),
            )
        clear_pending_login()
        flash("The verification window expired. Please sign in again.", "warning")
        return redirect(url_for("login"))

    if request.method == "POST":
        code = re.sub(r"\D", "", request.form.get("otp") or "")[:6]
        if len(code) != 6:
            flash("Enter the complete 6-digit code.", "error")
        elif not user["otp_code"] or not user["otp_expiry"]:
            flash("No active code. Request a new one.", "warning")
        elif int(user["otp_expiry"]) < now:
            flash("That code has expired. Request a new code.", "warning")
        elif (user["otp_attempts"] or 0) >= app.config["OTP_MAX_ATTEMPTS"]:
            with db.get_db() as conn:
                conn.execute(
                    """UPDATE users SET otp_code = NULL, otp_expiry = NULL,
                                        otp_attempts = 0 WHERE id = ?""",
                    (user["id"],),
                )
            clear_pending_login()
            flash("Too many incorrect codes. Please sign in again.", "error")
            return redirect(url_for("login"))
        elif otp_matches(code, user["otp_code"]):
            with db.get_db() as conn:
                conn.execute(
                    """UPDATE users
                       SET otp_code = NULL, otp_expiry = NULL, otp_attempts = 0,
                           last_login_at = ?
                       WHERE id = ?""",
                    (now, user["id"]),
                )
            session.clear()
            session.permanent = True
            session["user_id"] = user["id"]
            flash(f"Welcome back, {user['username']}. 2-step verification complete.", "success")
            return redirect(url_for("dashboard"))
        else:
            attempts = (user["otp_attempts"] or 0) + 1
            remaining = app.config["OTP_MAX_ATTEMPTS"] - attempts
            with db.get_db() as conn:
                conn.execute(
                    "UPDATE users SET otp_attempts = ? WHERE id = ?",
                    (attempts, user["id"]),
                )
            if remaining <= 0:
                with db.get_db() as conn:
                    conn.execute(
                        """UPDATE users SET otp_code = NULL, otp_expiry = NULL,
                                            otp_attempts = 0 WHERE id = ?""",
                        (user["id"],),
                    )
                clear_pending_login()
                flash("Too many incorrect codes. Please sign in again.", "error")
                return redirect(url_for("login"))
            flash(f"Incorrect code. {remaining} attempt(s) remaining.", "error")

    cooldown = 0
    if user["otp_last_sent"]:
        cooldown = max(
            0,
            app.config["OTP_RESEND_SECONDS"] - (now - int(user["otp_last_sent"])),
        )

    return render_template(
        "verify_2fa.html",
        username=user["username"],
        expires_at=int(user["otp_expiry"]) if user["otp_expiry"] else 0,
        cooldown=cooldown,
        demo_code=demo_code_for("login", user["id"]),
    )


@app.post("/verify-2fa/resend")
def resend_otp():
    user = fetch_user(session.get("pending_user_id"))
    if not user:
        clear_pending_login()
        flash("Your sign-in session expired. Please sign in again.", "warning")
        return redirect(url_for("login"))

    now = utc_now()
    if user["otp_last_sent"]:
        wait = app.config["OTP_RESEND_SECONDS"] - (now - int(user["otp_last_sent"]))
        if wait > 0:
            flash(f"Please wait {wait} second(s) before requesting another code.", "warning")
            return redirect(url_for("verify_2fa"))

    code = f"{secrets.randbelow(1_000_000):06d}"
    with db.get_db() as conn:
        conn.execute(
            """UPDATE users
               SET otp_code = ?, otp_expiry = ?, otp_attempts = 0, otp_last_sent = ?
               WHERE id = ?""",
            (
                hash_otp(code),
                now + app.config["OTP_TTL_SECONDS"],
                now,
                user["id"],
            ),
        )

    sent, message = deliver_code(user, code, "login")
    flash("A new verification code has been sent." if sent else message, "success" if sent else "warning")
    return redirect(url_for("verify_2fa"))


@app.post("/logout")
@login_required
def logout():
    session.clear()
    flash("You have signed out securely.", "success")
    return redirect(url_for("login"))


@app.get("/dashboard")
@login_required
def dashboard():
    user = fetch_user(session.get("user_id"))
    if not user:
        session.clear()
        flash("Your account could not be found. Please sign in again.", "warning")
        return redirect(url_for("login"))
    return render_template(
        "dashboard.html",
        user=user,
        member_since=datetime.fromtimestamp(user["created_at"], timezone.utc).strftime(
            "%d %b %Y"
        ),
        last_login=(
            datetime.fromtimestamp(user["last_login_at"], timezone.utc).strftime(
                "%d %b %Y, %H:%M UTC"
            )
            if user["last_login_at"]
            else "First verified sign-in"
        ),
    )


# ---------------------------------------------------------------------------
# Forgot / reset password
# ---------------------------------------------------------------------------
@app.route("/forgot-password", methods=["GET", "POST"])
def forgot_password():
    if request.method == "POST":
        email = normalize_email(request.form.get("email"))
        user = (
            db.get_db()
            .execute("SELECT * FROM users WHERE email = ? COLLATE NOCASE", (email,))
            .fetchone()
        )

        if user:
            now = utc_now()
            code = f"{secrets.randbelow(1_000_000):06d}"
            with db.get_db() as conn:
                conn.execute(
                    """UPDATE users
                       SET reset_code = ?, reset_expiry = ?, reset_attempts = 0,
                           reset_last_sent = ?
                       WHERE id = ?""",
                    (
                        hash_otp(code),
                        now + app.config["RESET_TTL_SECONDS"],
                        now,
                        user["id"],
                    ),
                )
            clear_pending_login()
            session["pending_reset_user_id"] = user["id"]
            session["pending_reset_started"] = now
            sent, message = deliver_code(user, code, "password_reset")
            if not sent:
                app.logger.warning("Password reset email fallback used for user %s", user["id"])

        # Same response whether or not the account exists.
        flash(
            "If an account exists for that email, a 6-digit reset code has been "
            "sent to the authorised inbox and printed in the server terminal.",
            "info",
        )
        return redirect(url_for("reset_password"))

    return render_template("forgot_password.html")


@app.route("/reset-password", methods=["GET", "POST"])
def reset_password():
    user = fetch_user(session.get("pending_reset_user_id"))
    now = utc_now()

    if request.method == "POST":
        code = re.sub(r"\D", "", request.form.get("otp") or "")[:6]
        password = request.form.get("password") or ""
        confirm = request.form.get("confirm_password") or ""

        if not user:
            flash("This password reset request is invalid or has expired.", "error")
            return redirect(url_for("forgot_password"))

        if now - int(session.get("pending_reset_started", 0)) > app.config["RESET_TTL_SECONDS"]:
            with db.get_db() as conn:
                conn.execute(
                    """UPDATE users SET reset_code = NULL, reset_expiry = NULL,
                                        reset_attempts = 0 WHERE id = ?""",
                    (user["id"],),
                )
            clear_pending_reset()
            flash("The reset code expired. Request a new one.", "warning")
            return redirect(url_for("forgot_password"))

        if not user["reset_code"] or not user["reset_expiry"]:
            flash("No active reset code. Request a new one.", "warning")
        elif int(user["reset_expiry"]) < now:
            flash("That reset code has expired. Request a new one.", "warning")
        elif (user["reset_attempts"] or 0) >= app.config["RESET_MAX_ATTEMPTS"]:
            with db.get_db() as conn:
                conn.execute(
                    """UPDATE users SET reset_code = NULL, reset_expiry = NULL,
                                        reset_attempts = 0 WHERE id = ?""",
                    (user["id"],),
                )
            clear_pending_reset()
            flash("Too many incorrect codes. Request a new reset code.", "error")
            return redirect(url_for("forgot_password"))
        elif len(code) != 6 or not otp_matches(code, user["reset_code"]):
            attempts = (user["reset_attempts"] or 0) + 1
            with db.get_db() as conn:
                conn.execute(
                    "UPDATE users SET reset_attempts = ? WHERE id = ?",
                    (attempts, user["id"]),
                )
            flash("Incorrect or incomplete reset code.", "error")
        else:
            policy = password_policy_errors(password)
            if policy:
                flash("Password must contain " + ", ".join(policy) + ".", "error")
            elif password != confirm:
                flash("Passwords do not match.", "error")
            else:
                with db.get_db() as conn:
                    conn.execute(
                        """UPDATE users
                           SET password_hash = ?, reset_code = NULL,
                               reset_expiry = NULL, reset_attempts = 0,
                               failed_logins = 0, locked_until = NULL
                           WHERE id = ?""",
                        (generate_password_hash(password), user["id"]),
                    )
                session.clear()
                flash(
                    "Password updated successfully. Sign in with your new password.",
                    "success",
                )
                return redirect(url_for("login"))

    if user:
        cooldown = 0
        if user["reset_last_sent"]:
            cooldown = max(
                0,
                app.config["OTP_RESEND_SECONDS"]
                - (now - int(user["reset_last_sent"])),
            )
    else:
        cooldown = 0

    return render_template(
        "reset_password.html",
        has_request=bool(user),
        expires_at=int(user["reset_expiry"]) if user and user["reset_expiry"] else 0,
        cooldown=cooldown,
        demo_code=demo_code_for("password_reset", user["id"]) if user else None,
    )


# ---------------------------------------------------------------------------
# Error handlers
# ---------------------------------------------------------------------------
@app.errorhandler(400)
def bad_request(error):
    return render_template("error.html", code=400, message=getattr(error, "description", "Bad request.")), 400


@app.errorhandler(404)
def not_found(_error):
    return render_template("error.html", code=404, message="The page you requested does not exist."), 404


@app.errorhandler(413)
def too_large(_error):
    return render_template("error.html", code=413, message="The request body is too large."), 413


@app.errorhandler(500)
def server_error(_error):
    db.close_db()
    return render_template("error.html", code=500, message="An unexpected error occurred. Please try again."), 500


def seed_demo_account() -> None:
    """Create the documented demo login on first run when demo mode is enabled."""
    if not app.config.get("DEMO_MODE"):
        return
    email = owner_inbox() or "demo@example.com"
    created = db.seed_demo_account(
        app.config["DATABASE_PATH"],
        username=app.config["DEMO_ACCOUNT_USERNAME"],
        email=email,
        password=app.config["DEMO_ACCOUNT_PASSWORD"],
    )
    if created:
        print(
            "  Demo login created: "
            f"{app.config['DEMO_ACCOUNT_USERNAME']} / "
            f"{app.config['DEMO_ACCOUNT_PASSWORD']}",
            flush=True,
        )


if __name__ == "__main__":
    debug = os.getenv("FLASK_DEBUG", "0") == "1"
    seed_demo_account()
    print("\n  Secure Login System")
    print(f"  URL      : http://{app.config['HOST']}:{app.config['PORT']}")
    print(f"  Database : {app.config['DATABASE_PATH']}")
    print(f"  OTP inbox: {owner_inbox() or 'not configured'}")
    print(
        "  Demo login: "
        f"{app.config['DEMO_ACCOUNT_USERNAME']} / {app.config['DEMO_ACCOUNT_PASSWORD']}"
    )
    print(
        "  OTP codes are emailed, shown on screen when delivery fails, "
        "and printed below.\n"
    )
    app.run(
        host=app.config["HOST"],
        port=app.config["PORT"],
        debug=debug,
        use_reloader=False,
    )
