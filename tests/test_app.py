"""End-to-end smoke tests for the Secure Login System.

Run with:  .venv/bin/python -m unittest discover -s tests -v
A temporary SQLite database is used; database.db is not touched.
SMTP is stubbed so the tests never send real email.
"""

from __future__ import annotations

import os
import sys
import tempfile
import unittest
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

import app as app_module  # noqa: E402
import db  # noqa: E402

PASSWORD = "StrongPass!23"
NEW_PASSWORD = "FreshPass!24"


class SecureLoginFlowTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.db_path = str(Path(self.tmp.name) / "test.db")
        app_module.app.config.update(
            TESTING=True,
            DATABASE_PATH=self.db_path,
            SECRET_KEY="test-secret-key-for-automated-tests-only",
            OTP_RECIPIENT_OVERRIDE="db1434@gmail.com",
            OTP_TTL_SECONDS=300,
            OTP_RESEND_SECONDS=60,
            OTP_MAX_ATTEMPTS=5,
            MAIL_USERNAME="",
            MAIL_PASSWORD="",
        )
        db.init_db(self.db_path)
        self.client = app_module.app.test_client()
        self.codes: dict[str, str] = {}
        self._original_deliver = app_module.deliver_code
        app_module.deliver_code = self._fake_deliver

    def tearDown(self) -> None:
        app_module.deliver_code = self._original_deliver
        self.tmp.cleanup()

    # -- helpers ---------------------------------------------------------
    def _fake_deliver(self, user, code, purpose):
        self.codes[purpose] = code
        return True, f"Test delivery for {user['email']}."

    def csrf(self, path: str) -> str:
        response = self.client.get(path)
        self.assertIn(response.status_code, (200, 302), path)
        with self.client.session_transaction() as sess:
            token = sess.get("_csrf_token")
        self.assertTrue(token, "CSRF token missing from session")
        return token

    def register(self, username="alex", email="alex@example.com", password=PASSWORD):
        token = self.csrf("/register")
        return self.client.post(
            "/register",
            data={
                "csrf_token": token,
                "username": username,
                "email": email,
                "password": password,
                "confirm_password": password,
            },
            follow_redirects=True,
        )

    def login(self, identifier="alex", password=PASSWORD, follow=False):
        token = self.csrf("/login")
        return self.client.post(
            "/login",
            data={
                "csrf_token": token,
                "identifier": identifier,
                "password": password,
            },
            follow_redirects=follow,
        )

    def verify(self, code: str):
        token = self.csrf("/verify-2fa")
        return self.client.post(
            "/verify-2fa",
            data={"csrf_token": token, "otp": code},
            follow_redirects=False,
        )

    def complete_login(self):
        response = self.login()
        self.assertEqual(response.status_code, 302)
        self.assertIn("/verify-2fa", response.headers["Location"])
        code = self.codes["login"]
        response = self.verify(code)
        self.assertEqual(response.status_code, 302)
        self.assertIn("/dashboard", response.headers["Location"])

    # -- tests -----------------------------------------------------------
    def test_01_pages_and_security_headers(self):
        for path in ("/login", "/register", "/forgot-password", "/reset-password"):
            response = self.client.get(path)
            self.assertEqual(response.status_code, 200, path)
            self.assertIn("text/html", response.mimetype)
            self.assertIn("default-src 'self'", response.headers["Content-Security-Policy"])
            self.assertEqual(response.headers["X-Frame-Options"], "DENY")
            self.assertEqual(response.headers["X-Content-Type-Options"], "nosniff")

        health = self.client.get("/healthz")
        self.assertEqual(health.status_code, 200)
        self.assertEqual(health.get_json()["status"], "ok")

    def test_02_register_hashes_password_and_rejects_duplicates(self):
        response = self.register()
        self.assertIn("Account created successfully", response.get_data(as_text=True))

        with db.connect(self.db_path) as conn:
            user = conn.execute("SELECT * FROM users WHERE username = 'alex'").fetchone()
        self.assertIsNotNone(user)
        self.assertNotEqual(user["password_hash"], PASSWORD)
        self.assertTrue(user["password_hash"].startswith("scrypt:"))
        self.assertEqual(user["email"], "alex@example.com")
        self.assertIsNone(user["otp_code"])

        duplicate = self.register(email="another@example.com")
        self.assertIn("already registered", duplicate.get_data(as_text=True))

    def test_03_wrong_password_is_rejected(self):
        self.register()
        response = self.login(password="WrongPassword!1", follow=True)
        self.assertIn("Invalid username/email or password", response.get_data(as_text=True))
        with db.connect(self.db_path) as conn:
            user = conn.execute("SELECT failed_logins FROM users WHERE username = 'alex'").fetchone()
        self.assertEqual(user["failed_logins"], 1)

    def test_04_full_two_factor_login_and_logout(self):
        self.register()
        response = self.login()
        self.assertEqual(response.status_code, 302)
        self.assertTrue(response.headers["Location"].endswith("/verify-2fa"))
        self.assertIn("login", self.codes)

        # Before verification the dashboard is still locked.
        blocked = self.client.get("/dashboard")
        self.assertEqual(blocked.status_code, 302)
        self.assertIn("/login", blocked.headers["Location"])

        # Wrong code is rejected.
        wrong = self.verify("000000" if self.codes["login"] != "000000" else "111111")
        self.assertEqual(wrong.status_code, 200)
        self.assertIn("Incorrect code", wrong.get_data(as_text=True))

        response = self.verify(self.codes["login"])
        self.assertEqual(response.status_code, 302)
        self.assertIn("/dashboard", response.headers["Location"])

        dashboard = self.client.get("/dashboard")
        body = dashboard.get_data(as_text=True)
        self.assertEqual(dashboard.status_code, 200)
        self.assertIn("Protected area", body)
        self.assertIn("alex@example.com", body)

        with db.connect(self.db_path) as conn:
            user = conn.execute("SELECT * FROM users WHERE username = 'alex'").fetchone()
        self.assertIsNone(user["otp_code"])
        self.assertIsNotNone(user["last_login_at"])

        token = self.csrf("/dashboard")
        logout = self.client.post(
            "/logout", data={"csrf_token": token}, follow_redirects=True
        )
        self.assertIn("signed out securely", logout.get_data(as_text=True))
        self.assertEqual(self.client.get("/dashboard").status_code, 302)

    def test_05_csrf_is_required(self):
        self.register()
        response = self.client.post(
            "/login", data={"identifier": "alex", "password": PASSWORD}
        )
        self.assertEqual(response.status_code, 400)
        self.assertIn("CSRF", response.get_data(as_text=True))

    def test_06_forgot_password_reset_flow(self):
        self.register()
        token = self.csrf("/forgot-password")
        response = self.client.post(
            "/forgot-password",
            data={"csrf_token": token, "email": "alex@example.com"},
            follow_redirects=False,
        )
        self.assertEqual(response.status_code, 302)
        self.assertIn("/reset-password", response.headers["Location"])
        self.assertIn("password_reset", self.codes)
        reset_code = self.codes["password_reset"]

        token = self.csrf("/reset-password")
        response = self.client.post(
            "/reset-password",
            data={
                "csrf_token": token,
                "otp": reset_code,
                "password": NEW_PASSWORD,
                "confirm_password": NEW_PASSWORD,
            },
            follow_redirects=True,
        )
        self.assertIn("Password updated successfully", response.get_data(as_text=True))

        # Old password no longer works; new password starts a fresh 2FA challenge.
        old = self.login(password=PASSWORD, follow=True)
        self.assertIn("Invalid username/email or password", old.get_data(as_text=True))

        self.codes.clear()
        response = self.login(password=NEW_PASSWORD)
        self.assertEqual(response.status_code, 302)
        self.assertIn("login", self.codes)

    def test_07_login_lockout_after_repeated_failures(self):
        self.register()
        for _ in range(5):
            self.login(password="WrongPassword!1")
        locked = self.login(password=PASSWORD, follow=True)
        self.assertEqual(locked.status_code, 429)
        self.assertIn("Too many failed attempts", locked.get_data(as_text=True))

    def test_08_otp_attempt_limit(self):
        self.register()
        self.login()
        real_code = self.codes["login"]
        wrong_codes = ["000000", "111111", "222222", "333333", "444444"]
        wrong_codes = [c for c in wrong_codes if c != real_code][:5]
        for code in wrong_codes:
            response = self.verify(code)
        self.assertEqual(response.status_code, 302)
        self.assertIn("/login", response.headers["Location"])
        self.assertEqual(self.client.get("/dashboard").status_code, 302)

    def test_09_reset_password_requires_matching_passwords(self):
        self.register()
        token = self.csrf("/forgot-password")
        self.client.post(
            "/forgot-password",
            data={"csrf_token": token, "email": "alex@example.com"},
        )
        reset_code = self.codes["password_reset"]
        token = self.csrf("/reset-password")
        response = self.client.post(
            "/reset-password",
            data={
                "csrf_token": token,
                "otp": reset_code,
                "password": NEW_PASSWORD,
                "confirm_password": "DifferentPass!25",
            },
            follow_redirects=True,
        )
        self.assertIn("Passwords do not match", response.get_data(as_text=True))


if __name__ == "__main__":
    unittest.main(verbosity=2)
