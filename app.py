"""
app.py - Secure Login System (Flask + SQLite)

Features:
  * User registration with strong password hashing (Werkzeug / scrypt-pbkdf2)
  * Two-Step Verification (2FA): valid credentials -> 6-digit OTP -> dashboard
  * OTP generated with the `secrets` module, stored in DB with an expiry timestamp
  * OTP printed clearly in the server console for easy testing (no SMTP/SMS needed)
  * Session-based protected dashboard and logout
"""

import hmac
import os
import secrets
import smtplib
import time
from email.message import EmailMessage
from functools import wraps

from flask import (
    Flask,
    flash,
    redirect,
    render_template,
    request,
    session,
    url_for,
)
from werkzeug.security import check_password_hash, generate_password_hash

from env_utils import load_env_file
from init_db import get_connection, init_db

# Load optional local credentials (.env) before reading any environment values.
load_env_file()

# --------------------------------------------------------------------------- #
# App configuration
# --------------------------------------------------------------------------- #
app = Flask(__name__)
# Use a stable secret from the environment when provided; otherwise generate a
# fresh one per start (sessions simply reset when the server is restarted).
app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY") or secrets.token_hex(32)
app.config["SESSION_COOKIE_HTTPONLY"] = True
app.config["SESSION_COOKIE_SAMESITE"] = "Lax"

OTP_VALID_SECONDS = 300          # Login OTP is valid for 5 minutes
RESET_VALID_SECONDS = 900        # Password reset code is valid for 15 minutes
MAX_OTP_ATTEMPTS = 5             # Basic brute-force protection on OTP forms

# Gmail SMTP delivery. Credentials are read from environment variables / .env
# only - they are NEVER stored in the source code or the database.
GMAIL_ADDRESS = os.environ.get("GMAIL_ADDRESS", "")
GMAIL_APP_PASSWORD = os.environ.get("GMAIL_APP_PASSWORD", "")

# "email" = send the code by email only (no terminal/banner fallback).
# "demo"  = show the code in the terminal and testing banner (no SMTP needed).
OTP_DELIVERY = os.environ.get("OTP_DELIVERY", "email").strip().lower()
if OTP_DELIVERY not in ("email", "demo"):
    OTP_DELIVERY = "email"


def email_configured():
    """True when both Gmail credentials are present."""
    return bool(GMAIL_ADDRESS and GMAIL_APP_PASSWORD)

# Make sure the database exists before the first request. A demo account is
# seeded on first run so the system can be demonstrated immediately.
init_db(seed_demo=True)


# --------------------------------------------------------------------------- #
# Helpers
# --------------------------------------------------------------------------- #
def generate_otp():
    """Return a cryptographically secure random 6-digit OTP string."""
    return str(secrets.randbelow(900000) + 100000)


def print_otp_to_terminal(username, otp):
    """Print the OTP prominently so it can be used without any external service."""
    print("\n" + "=" * 64)
    print("  [2FA] Two-Step Verification OTP")
    print("  User    : {}".format(username))
    print("  OTP     : {}".format(otp))
    print("  Valid   : {} seconds ({} minutes)".format(OTP_VALID_SECONDS, OTP_VALID_SECONDS // 60))
    print("=" * 64 + "\n", flush=True)


def send_code_email(to_email, username, code, purpose="login"):
    """Best-effort delivery of a 6-digit code via Gmail SMTP.

    Returns True only when the message was actually sent. When SMTP is not
    configured (or sending fails), the code is still available in the terminal
    and in the on-page testing banner, so the flow never breaks.
    """
    if not email_configured():
        if OTP_DELIVERY == "email":
            print("[mail] ERROR: email-only mode but GMAIL_ADDRESS / GMAIL_APP_PASSWORD "
                  "are not configured. Codes cannot be delivered.", flush=True)
        else:
            print("[mail] SMTP not configured; using terminal + banner instead.", flush=True)
        return False

    if purpose == "reset":
        subject = "Reset your SecureAuth password"
        label = "password reset code"
        valid_minutes = RESET_VALID_SECONDS // 60
    else:
        subject = "Your SecureAuth verification code"
        label = "one-time verification (OTP) code"
        valid_minutes = OTP_VALID_SECONDS // 60

    message = EmailMessage()
    message["Subject"] = subject
    message["From"] = GMAIL_ADDRESS
    message["To"] = to_email
    message.set_content(
        "Hello {},\n\n"
        "Your {} is: {}\n\n"
        "It expires in {} minutes. If you did not request this code, "
        "you can safely ignore this message.\n\n"
        "- SecureAuth\n".format(username, label, code, valid_minutes)
    )

    try:
        with smtplib.SMTP_SSL("smtp.gmail.com", 465, timeout=10) as smtp:
            smtp.login(GMAIL_ADDRESS, GMAIL_APP_PASSWORD)
            smtp.send_message(message)
        print("[mail] Email sent to {} ({})".format(to_email, purpose), flush=True)
        return True
    except Exception as exc:
        print("[mail] Could not send email: {}".format(exc), flush=True)
        return False


def print_reset_to_terminal(username, code):
    """Print the password reset code prominently in the server terminal."""
    print("\n" + "=" * 64)
    print("  [RESET] Password Reset Code")
    print("  User    : {}".format(username))
    print("  Code    : {}".format(code))
    print("  Valid   : {} seconds ({} minutes)".format(RESET_VALID_SECONDS, RESET_VALID_SECONDS // 60))
    print("=" * 64 + "\n", flush=True)


def login_required(view):
    """Decorator that redirects unauthenticated users to the login page."""
    @wraps(view)
    def wrapped(*args, **kwargs):
        if not session.get("authenticated"):
            flash("Please log in to access that page.", "danger")
            return redirect(url_for("login"))
        return view(*args, **kwargs)

    return wrapped


def clear_otp(user_id):
    """Remove OTP data for a user after success, expiry, or too many attempts."""
    conn = get_connection()
    conn.execute(
        "UPDATE users SET otp_code = NULL, otp_expiry = NULL WHERE id = ?",
        (user_id,),
    )
    conn.commit()
    conn.close()


def clear_reset(user_id):
    """Remove password-reset data after success, expiry, or too many attempts."""
    conn = get_connection()
    conn.execute(
        "UPDATE users SET reset_code = NULL, reset_expiry = NULL WHERE id = ?",
        (user_id,),
    )
    conn.commit()
    conn.close()


def clear_reset_session():
    """Remove password-reset state from the session."""
    for key in ("reset_pending", "reset_user_id", "reset_email", "reset_attempts", "reset_emailed"):
        session.pop(key, None)


# --------------------------------------------------------------------------- #
# Routes
# --------------------------------------------------------------------------- #
@app.route("/")
def index():
    if session.get("authenticated"):
        return redirect(url_for("dashboard"))
    return redirect(url_for("login"))


@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        confirm = request.form.get("confirm_password", "")

        # ---- validation ----
        if not username or not email or not password:
            flash("All fields are required.", "danger")
        elif len(username) < 3:
            flash("Username must be at least 3 characters long.", "danger")
        elif "@" not in email or "." not in email:
            flash("Please enter a valid email address.", "danger")
        elif len(password) < 8:
            flash("Password must be at least 8 characters long.", "danger")
        elif password != confirm:
            flash("Passwords do not match.", "danger")
        else:
            # ---- hash the password before storage ----
            password_hash = generate_password_hash(password)
            conn = get_connection()
            try:
                conn.execute(
                    "INSERT INTO users (username, email, password_hash) VALUES (?, ?, ?)",
                    (username, email, password_hash),
                )
                conn.commit()
                flash("Registration successful. Please log in.", "success")
                return redirect(url_for("login"))
            except Exception:
                # UNIQUE constraint on username / email
                flash("That username or email is already registered.", "danger")
            finally:
                conn.close()

    return render_template("register.html")


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        identifier = request.form.get("identifier", "").strip()
        password = request.form.get("password", "")

        conn = get_connection()
        user = conn.execute(
            "SELECT * FROM users WHERE username = ? OR email = ?",
            (identifier, identifier.lower()),
        ).fetchone()
        conn.close()

        # ---- verify the hashed password ----
        if user and check_password_hash(user["password_hash"], password):
            # In email-only mode the server cannot continue without SMTP.
            if OTP_DELIVERY == "email" and not email_configured():
                flash("Email delivery is not configured on the server. Add "
                      "GMAIL_APP_PASSWORD to .env and restart.", "danger")
                return render_template("login.html")

            otp = generate_otp()
            expiry = int(time.time()) + OTP_VALID_SECONDS

            # ---- save OTP + expiry in the database ----
            conn = get_connection()
            conn.execute(
                "UPDATE users SET otp_code = ?, otp_expiry = ? WHERE id = ?",
                (otp, expiry, user["id"]),
            )
            conn.commit()
            conn.close()

            # In email-only mode the code is never printed or shown on screen.
            emailed = send_code_email(user["email"], user["username"], otp, "login")
            if not emailed and OTP_DELIVERY != "email":
                print_otp_to_terminal(user["username"], otp)

            session["otp_pending"] = True
            session["otp_emailed"] = emailed
            session["pending_user_id"] = user["id"]
            session["pending_username"] = user["username"]
            session["otp_attempts"] = 0
            hint = ("Credentials accepted. Check your email for the 6-digit OTP."
                    if emailed else
                    "Credentials accepted. Enter the 6-digit OTP shown below to continue.")
            flash(hint, "info")
            return redirect(url_for("verify_2fa"))

        # Generic error avoids revealing whether the username or password was wrong.
        flash("Invalid username/email or password.", "danger")

    return render_template("login.html")


@app.route("/verify-2fa", methods=["GET", "POST"])
def verify_2fa():
    if not session.get("otp_pending"):
        flash("Please log in first to receive an OTP.", "danger")
        return redirect(url_for("login"))

    user_id = session["pending_user_id"]
    username = session["pending_username"]

    if request.method == "POST":
        submitted = request.form.get("otp", "").strip()

        conn = get_connection()
        user = conn.execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()
        conn.close()

        if not user or not user["otp_code"]:
            flash("No active OTP found. Please log in again.", "danger")
            session.clear()
            return redirect(url_for("login"))

        # ---- check expiry ----
        if user["otp_expiry"] is None or user["otp_expiry"] < int(time.time()):
            clear_otp(user_id)
            flash("The OTP has expired. Please log in again.", "danger")
            session.clear()
            return redirect(url_for("login"))

        # ---- constant-time comparison of the OTP ----
        if hmac.compare_digest(submitted, user["otp_code"]):
            clear_otp(user_id)
            session.clear()
            session["authenticated"] = True
            session["user_id"] = user["id"]
            session["username"] = user["username"]
            flash("Two-step verification successful. Welcome, {}!".format(user["username"]), "success")
            return redirect(url_for("dashboard"))

        # ---- wrong OTP: basic brute-force protection ----
        session["otp_attempts"] = session.get("otp_attempts", 0) + 1
        attempts_left = MAX_OTP_ATTEMPTS - session["otp_attempts"]
        if attempts_left <= 0:
            clear_otp(user_id)
            session.clear()
            flash("Too many incorrect attempts. Please log in again.", "danger")
            return redirect(url_for("login"))
        flash("Incorrect OTP. {} attempt(s) remaining.".format(attempts_left), "danger")

    # Testing banner value: only the OTP owner's session reaches this page.
    conn = get_connection()
    active = conn.execute("SELECT otp_code FROM users WHERE id = ?", (user_id,)).fetchone()
    conn.close()
    # In email-only mode the code is never shown on screen. In demo mode it is
    # hidden once an email was sent successfully.
    show_code = OTP_DELIVERY != "email" and not session.get("otp_emailed")
    testing_otp = (active["otp_code"] if active else None) if show_code else None

    return render_template(
        "verify_2fa.html",
        username=username,
        testing_otp=testing_otp,
        valid_seconds=OTP_VALID_SECONDS,
    )


@app.route("/resend-otp", methods=["POST"])
def resend_otp():
    if not session.get("otp_pending"):
        return redirect(url_for("login"))

    if OTP_DELIVERY == "email" and not email_configured():
        flash("Email delivery is not configured on the server.", "danger")
        return redirect(url_for("verify_2fa"))

    user_id = session["pending_user_id"]
    username = session["pending_username"]
    otp = generate_otp()
    expiry = int(time.time()) + OTP_VALID_SECONDS

    conn = get_connection()
    conn.execute(
        "UPDATE users SET otp_code = ?, otp_expiry = ? WHERE id = ?",
        (otp, expiry, user_id),
    )
    conn.commit()
    conn.close()

    conn = get_connection()
    user = conn.execute("SELECT email FROM users WHERE id = ?", (user_id,)).fetchone()
    conn.close()
    emailed = send_code_email(user["email"], username, otp, "login") if user else False
    if not emailed and OTP_DELIVERY != "email":
        print_otp_to_terminal(username, otp)

    session["otp_attempts"] = 0
    session["otp_emailed"] = emailed
    hint = ("A new OTP has been sent to your email."
            if emailed else
            "A new OTP has been generated (see the testing banner / terminal).")
    flash(hint, "info")
    return redirect(url_for("verify_2fa"))


@app.route("/forgot-password", methods=["GET", "POST"])
def forgot_password():
    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()

        conn = get_connection()
        user = conn.execute("SELECT * FROM users WHERE email = ?", (email,)).fetchone()

        if user:
            if OTP_DELIVERY == "email" and not email_configured():
                conn.close()
                flash("Email delivery is not configured on the server. Add "
                      "GMAIL_APP_PASSWORD to .env and restart.", "danger")
                return render_template("forgot_password.html")

            code = generate_otp()
            expiry = int(time.time()) + RESET_VALID_SECONDS
            conn.execute(
                "UPDATE users SET reset_code = ?, reset_expiry = ? WHERE id = ?",
                (code, expiry, user["id"]),
            )
            conn.commit()
            conn.close()

            emailed = send_code_email(user["email"], user["username"], code, "reset")
            if not emailed and OTP_DELIVERY != "email":
                print_reset_to_terminal(user["username"], code)

            session["reset_pending"] = True
            session["reset_user_id"] = user["id"]
            session["reset_email"] = user["email"]
            session["reset_attempts"] = 0
            session["reset_emailed"] = emailed
            hint = ("A password reset code has been sent to your email."
                    if emailed else
                    "A password reset code has been generated (see the testing banner / terminal).")
            flash(hint, "info")
            return redirect(url_for("reset_password"))

        conn.close()
        # Generic wording prevents attackers from enumerating registered emails.
        flash("If an account exists for that email, a reset code has been generated.", "info")

    return render_template("forgot_password.html")


@app.route("/reset-password", methods=["GET", "POST"])
def reset_password():
    if not session.get("reset_pending"):
        flash("Please request a password reset code first.", "danger")
        return redirect(url_for("forgot_password"))

    user_id = session["reset_user_id"]
    email = session.get("reset_email", "")

    conn = get_connection()
    user = conn.execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()
    conn.close()

    if not user or not user["reset_code"]:
        clear_reset_session()
        flash("No active reset code. Please request a new one.", "danger")
        return redirect(url_for("forgot_password"))

    if request.method == "POST":
        code = request.form.get("code", "").strip()
        new_password = request.form.get("new_password", "")
        confirm = request.form.get("confirm_password", "")

        # ---- check expiry ----
        if user["reset_expiry"] is None or user["reset_expiry"] < int(time.time()):
            clear_reset(user_id)
            clear_reset_session()
            flash("The reset code has expired. Please request a new one.", "danger")
            return redirect(url_for("forgot_password"))

        # ---- constant-time comparison ----
        if not hmac.compare_digest(code, user["reset_code"]):
            session["reset_attempts"] = session.get("reset_attempts", 0) + 1
            attempts_left = MAX_OTP_ATTEMPTS - session["reset_attempts"]
            if attempts_left <= 0:
                clear_reset(user_id)
                clear_reset_session()
                flash("Too many incorrect attempts. Please request a new code.", "danger")
                return redirect(url_for("forgot_password"))
            flash("Incorrect reset code. {} attempt(s) remaining.".format(attempts_left), "danger")
        elif len(new_password) < 8:
            flash("Password must be at least 8 characters long.", "danger")
        elif new_password != confirm:
            flash("Passwords do not match.", "danger")
        else:
            # ---- store a fresh hash; never the plain-text password ----
            conn = get_connection()
            conn.execute(
                "UPDATE users SET password_hash = ?, reset_code = NULL, reset_expiry = NULL, "
                "otp_code = NULL, otp_expiry = NULL WHERE id = ?",
                (generate_password_hash(new_password), user_id),
            )
            conn.commit()
            conn.close()
            clear_reset_session()
            flash("Password reset successful. Please log in with your new password.", "success")
            return redirect(url_for("login"))

    # In email-only mode the reset code is never shown on screen.
    show_code = OTP_DELIVERY != "email" and not session.get("reset_emailed")
    testing_code = user["reset_code"] if show_code else None

    return render_template(
        "reset_password.html",
        email=email,
        testing_code=testing_code,
        valid_seconds=RESET_VALID_SECONDS,
    )


@app.route("/resend-reset", methods=["POST"])
def resend_reset():
    if not session.get("reset_pending"):
        return redirect(url_for("forgot_password"))

    if OTP_DELIVERY == "email" and not email_configured():
        flash("Email delivery is not configured on the server.", "danger")
        return redirect(url_for("reset_password"))

    user_id = session["reset_user_id"]
    conn = get_connection()
    user = conn.execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()
    if not user:
        conn.close()
        clear_reset_session()
        flash("Please request a new reset code.", "danger")
        return redirect(url_for("forgot_password"))

    code = generate_otp()
    expiry = int(time.time()) + RESET_VALID_SECONDS
    conn.execute(
        "UPDATE users SET reset_code = ?, reset_expiry = ? WHERE id = ?",
        (code, expiry, user_id),
    )
    conn.commit()
    conn.close()

    emailed = send_code_email(user["email"], user["username"], code, "reset")
    if not emailed and OTP_DELIVERY != "email":
        print_reset_to_terminal(user["username"], code)
    session["reset_attempts"] = 0
    session["reset_emailed"] = emailed
    hint = ("A new reset code has been sent to your email."
            if emailed else
            "A new reset code has been generated (see the testing banner / terminal).")
    flash(hint, "info")
    return redirect(url_for("reset_password"))


@app.route("/dashboard")
@login_required
def dashboard():
    conn = get_connection()
    user = conn.execute(
        "SELECT id, username, email, created_at FROM users WHERE id = ?",
        (session["user_id"],),
    ).fetchone()
    conn.close()
    return render_template("dashboard.html", user=user)


@app.route("/logout")
def logout():
    session.clear()
    flash("You have been logged out successfully.", "info")
    return redirect(url_for("login"))


if __name__ == "__main__":
    # host 0.0.0.0 makes it reachable from other devices on the network too.
    app.run(host="0.0.0.0", port=5000, debug=True)
