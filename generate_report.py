"""
generate_report.py - Automatically produce Assignment_Report.pdf

Uses fpdf2. All content is plain ASCII so the built-in Helvetica/Courier core
fonts can render it without any external font files.

Run:  python generate_report.py
"""

import os
from datetime import date

from fpdf import FPDF
from fpdf.enums import XPos, YPos

OUTPUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "Assignment_Report.pdf")

NAVY = (30, 41, 59)
PRIMARY = (79, 70, 229)
ACCENT = (6, 182, 212)
MUTED = (100, 116, 139)
LIGHT = (241, 245, 249)
BORDER = (203, 213, 225)
WHITE = (255, 255, 255)


class Report(FPDF):
    def __init__(self):
        super().__init__(orientation="P", unit="mm", format="A4")
        self.set_auto_page_break(auto=True, margin=20)
        self.set_margins(20, 20, 20)
        self.cover = True

    # ----- running header / footer (hidden on the cover) -----
    def header(self):
        if self.cover:
            return
        self.set_font("Helvetica", "B", 8)
        self.set_text_color(*MUTED)
        self.cell(0, 6, "SECURE LOGIN SYSTEM  -  ASSIGNMENT REPORT", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        self.set_draw_color(*BORDER)
        self.line(20, self.get_y(), 190, self.get_y())
        self.ln(4)

    def footer(self):
        if self.cover:
            return
        self.set_y(-15)
        self.set_font("Helvetica", "I", 8)
        self.set_text_color(*MUTED)
        self.cell(0, 10, "Page {}   |   Generated automatically by generate_report.py".format(self.page_no()),
                  align="C")

    # ----- content helpers -----
    def title_page(self):
        self.add_page()
        self.set_fill_color(*PRIMARY)
        self.rect(0, 0, 210, 72, "F")
        self.set_fill_color(*ACCENT)
        self.rect(0, 72, 210, 4, "F")

        self.set_xy(20, 22)
        self.set_font("Helvetica", "B", 27)
        self.set_text_color(*WHITE)
        self.multi_cell(170, 12, "Secure Login System", align="C",
                        new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        self.set_font("Helvetica", "", 13)
        self.set_text_color(224, 242, 254)
        self.multi_cell(170, 8, "Two-Step Verification and Password Hashing", align="C",
                        new_x=XPos.LMARGIN, new_y=YPos.NEXT)

        self.set_xy(20, 100)
        self.set_font("Helvetica", "B", 16)
        self.set_text_color(*PRIMARY)
        self.multi_cell(170, 10, "ASSIGNMENT REPORT", align="C",
                        new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        self.set_font("Helvetica", "", 11)
        self.set_text_color(*MUTED)
        self.multi_cell(170, 7, "Full-Stack Web Application with SQLite Database", align="C",
                        new_x=XPos.LMARGIN, new_y=YPos.NEXT)

        self.ln(14)
        info = [
            ("COURSE", "Secure Software Development / Web Technologies"),
            ("TOPIC", "Secure Authentication with 2FA and Password Hashing"),
            ("TECH STACK", "Python, Flask, SQLite, HTML/CSS, fpdf2"),
            ("DATE", date.today().strftime("%B %d, %Y")),
            ("STATUS", "Complete - ready to run"),
        ]
        for label, value in info:
            self.set_font("Helvetica", "B", 10)
            self.set_text_color(*NAVY)
            self.cell(38, 8, label)
            self.set_font("Helvetica", "", 10)
            self.set_text_color(*MUTED)
            self.multi_cell(132, 8, value, new_x=XPos.LMARGIN, new_y=YPos.NEXT)

        self.ln(10)
        self.set_fill_color(*LIGHT)
        self.set_draw_color(*BORDER)
        self.set_font("Helvetica", "I", 9)
        self.set_text_color(*MUTED)
        self.multi_cell(170, 6,
                        "Note: This document was generated automatically by the "
                        "generate_report.py script included in the project.",
                        border=1, fill=True, align="C",
                        new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        self.cover = False

    def h1(self, number, text):
        self.ln(3)
        self.set_fill_color(*PRIMARY)
        self.set_text_color(*WHITE)
        self.set_font("Helvetica", "B", 13)
        self.cell(0, 9, "  {}. {}".format(number, text), fill=True,
                  new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        self.ln(4)
        self.set_text_color(*NAVY)

    def h2(self, text):
        self.ln(2)
        self.set_font("Helvetica", "B", 11)
        self.set_text_color(*PRIMARY)
        self.multi_cell(0, 6, text, new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        self.ln(1)
        self.set_text_color(*NAVY)

    def body(self, text, size=10.5):
        self.set_font("Helvetica", "", size)
        self.set_text_color(45, 55, 72)
        self.multi_cell(0, 5.8, text, new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        self.ln(2)

    def bullet(self, text):
        self.set_font("Helvetica", "", 10.5)
        self.set_text_color(45, 55, 72)
        self.cell(6, 5.8, "-")
        self.multi_cell(0, 5.8, text, new_x=XPos.LMARGIN, new_y=YPos.NEXT)

    def numbered(self, number, text):
        self.set_font("Helvetica", "B", 10.5)
        self.set_text_color(*PRIMARY)
        self.cell(8, 6, "{}).".format(number))
        self.set_font("Helvetica", "", 10.5)
        self.set_text_color(45, 55, 72)
        self.multi_cell(0, 6, text, new_x=XPos.LMARGIN, new_y=YPos.NEXT)

    def code(self, text, size=8):
        self.ln(1)
        self.set_fill_color(*LIGHT)
        self.set_draw_color(*BORDER)
        self.set_font("Courier", "", size)
        self.set_text_color(*NAVY)
        self.multi_cell(0, 4.5, text, border=1, fill=True,
                        new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        self.ln(3)

    def caption(self, text):
        self.set_font("Helvetica", "I", 9)
        self.set_text_color(*MUTED)
        self.multi_cell(0, 5, text, new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        self.ln(1)

    def table(self, headers, rows, widths):
        self.set_font("Helvetica", "B", 9)
        self.set_fill_color(*PRIMARY)
        self.set_text_color(*WHITE)
        for w, h in zip(widths, headers):
            self.cell(w, 8, h, border=1, fill=True, align="C")
        self.ln()
        self.set_font("Helvetica", "", 9)
        self.set_text_color(*NAVY)
        for i, row in enumerate(rows):
            self.set_fill_color(*LIGHT) if i % 2 == 0 else self.set_fill_color(*WHITE)
            for w, val in zip(widths, row):
                self.cell(w, 8, val, border=1, fill=True)
            self.ln()
        self.ln(3)


def build_report():
    pdf = Report()
    pdf.title_page()

    # ---------------- 1. Project Overview ----------------
    pdf.add_page()
    pdf.h1(1, "Project Overview")
    pdf.body(
        "This project is a complete, full-stack Secure Login System built with Python "
        "and the Flask web framework. It stores user data in a local SQLite database "
        "(database.db), so it runs out-of-the-box without any external database server. "
        "The system goes beyond a simple username/password form by implementing Two-Step "
        "Verification (2FA) as the primary security mechanism."
    )
    pdf.body(
        "When a user registers, their password is transformed into a strong one-way hash "
        "before it is saved - the plain-text password is never stored. When that user logs "
        "in with valid credentials, the server generates a random 6-digit One-Time Password "
        "(OTP), saves it in the database together with an expiration timestamp, and asks "
        "for the code on a separate verification page. Only after the correct, unexpired OTP "
        "is supplied is an authenticated session created and the protected dashboard made "
        "available."
    )
    pdf.h2("Main Features")
    for item in [
        "User registration with validation and strong password hashing.",
        "Login by username or email with hashed-password verification.",
        "Cryptographically random 6-digit OTP with a 5-minute expiry.",
        "Email-only OTP delivery by default: the code is never shown on the server screen.",
        "Optional demo mode can print the OTP in the terminal and testing banner.",
        "Gmail SMTP credentials read from a local .env file or environment variables only.",
        "Session-based protected dashboard and secure logout.",
        "Forgot-password flow with an expiring reset code and a re-hashed new password.",
        "Automatic SQLite database initialization and a seeded demo account.",
        "Basic brute-force protection: OTP attempts are limited and expired codes are cleared.",
        "Automatically generated professional PDF report (this document).",
    ]:
        pdf.bullet(item)
    pdf.ln(2)
    pdf.h2("Contents of This Report")
    for item in [
        "1. Project Overview",
        "2. System Architecture and Tech Stack",
        "3. Database Schema and Connection Details",
        "4. Security Implementation Analysis (2FA and Password Hashing)",
        "5. Key Code Snippets",
        "6. Step-by-Step Instructions to Run the Project",
        "7. Conclusion",
    ]:
        pdf.bullet(item)

    # ---------------- 2. Architecture ----------------
    pdf.add_page()
    pdf.h1(2, "System Architecture and Tech Stack")
    pdf.body(
        "The application follows a classic three-layer web architecture. The browser "
        "(HTML/CSS front end) sends requests to Flask routes, which contain all business "
        "and security logic. Flask talks to the SQLite database through Python's built-in "
        "sqlite3 module. Werkzeug provides the password-hashing primitives, and the Python "
        "secrets module generates OTPs."
    )
    pdf.h2("Request / Authentication Flow")
    pdf.code(
        "  Browser\n"
        "     |  (1) POST /register --------------------> hash password -> INSERT into users\n"
        "     |\n"
        "     |  (2) POST /login with username + password\n"
        "     |            |\n"
        "     |            v\n"
        "     |      Flask route -> SELECT user -> check_password_hash()\n"
        "     |            |\n"
        "     |      valid credentials:\n"
        "     |            v\n"
        "     |      secrets.randbelow() -> 6-digit OTP\n"
        "     |      UPDATE users SET otp_code, otp_expiry\n"
        "     |      print OTP to terminal\n"
        "     |            |\n"
        "     |            v\n"
        "     |  (3) /verify-2fa  -> compare OTP + check expiry\n"
        "     |            |\n"
        "     |      correct & not expired:\n"
        "     |            v\n"
        "     |  (4) /dashboard  <-- authenticated session cookie\n"
        "     |\n"
        "     |  (5) /logout -> clear session"
    )
    pdf.caption("Figure 1: End-to-end authentication flow with the OTP as the second step.")
    pdf.h2("Technology Stack")
    pdf.table(
        ["LAYER", "TECHNOLOGY", "PURPOSE"],
        [
            ["Front end", "HTML5, CSS3", "Responsive pages for register/login/2FA/dashboard"],
            ["Back end", "Python 3 + Flask", "Routing, templates, sessions, security logic"],
            ["Database", "SQLite 3", "Local file database (database.db), no server needed"],
            ["Hashing", "Werkzeug security", "generate_password_hash / check_password_hash"],
            ["OTP", "Python secrets", "Cryptographically secure 6-digit OTP generation"],
            ["Reporting", "fpdf2", "Automatic generation of Assignment_Report.pdf"],
        ],
        [28, 38, 104],
    )

    # ---------------- 3. Database ----------------
    pdf.add_page()
    pdf.h1(3, "Database Schema and Connection Details")
    pdf.body(
        "The database is a single local file named database.db located in the project root. "
        "It is created automatically by init_db.py, which the Flask app calls on startup. "
        "The script uses CREATE TABLE IF NOT EXISTS, so running it repeatedly is safe and "
        "will not destroy existing data. A demo account is seeded on first run for testing."
    )
    pdf.h2("users Table")
    pdf.table(
        ["COLUMN", "TYPE", "DESCRIPTION"],
        [
            ["id", "INTEGER", "Primary key, auto-incrementing unique user ID"],
            ["username", "TEXT (UNIQUE)", "Unique login name chosen by the user"],
            ["email", "TEXT (UNIQUE)", "Unique email address; also usable for login"],
            ["password_hash", "TEXT", "One-way salted hash of the password (never plain text)"],
            ["otp_code", "TEXT", "Current 6-digit OTP, or NULL when none is active"],
            ["otp_expiry", "INTEGER", "Unix timestamp when the OTP stops being valid"],
            ["reset_code", "TEXT", "6-digit password-reset code (NULL when unused)"],
            ["reset_expiry", "INTEGER", "Unix timestamp when the reset code expires"],
            ["created_at", "TIMESTAMP", "Registration time (DEFAULT CURRENT_TIMESTAMP)"],
        ],
        [32, 32, 106],
    )
    pdf.h2("Connection Setup")
    pdf.code(
        "DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'database.db')\n\n"
        "def get_connection():\n"
        "    conn = sqlite3.connect(DB_PATH)\n"
        "    conn.row_factory = sqlite3.Row   # access columns by name\n"
        "    return conn"
    )
    pdf.caption("Code snippet 1: database connection (init_db.py).")
    pdf.body(
        "The absolute path based on __file__ guarantees that the correct database.db is "
        "used regardless of the directory from which the application is launched. Because "
        "SQLite is embedded in Python, there is no database server to install, configure, "
        "or start - this is what makes the project run out-of-the-box."
    )
    pdf.h2("OTP Storage Lifecycle")
    pdf.body(
        "On login, otp_code and otp_expiry are written for that user. On successful "
        "verification, on expiry, or after too many wrong attempts, both fields are reset "
        "to NULL by the clear_otp() helper so that a code can never be reused."
    )

    # ---------------- 4. Security Analysis ----------------
    pdf.add_page()
    pdf.h1(4, "Security Implementation Analysis")
    pdf.body(
        "This section explains in detail how the two core mechanisms - Two-Step "
        "Verification and Password Hashing - work together to protect against "
        "unauthorized access."
    )

    pdf.h2("4.1 Two-Step Verification (2FA)")
    pdf.body(
        "2FA requires two independent pieces of evidence before access is granted: "
        "something the user knows (the password) and something the user possesses at that "
        "moment (the one-time code). The first factor is checked on /login. Only if it "
        "passes does the server generate the second factor and redirect to /verify-2fa. "
        "This means that even if an attacker steals or guesses a password, they still "
        "cannot reach the dashboard without the current OTP."
    )
    pdf.body(
        "The OTP is created with secrets.randbelow(900000) + 100000, guaranteeing a "
        "uniformly random 6-digit value in the range 100000-999999. Using the secrets "
        "module (rather than random) is important because it draws on the operating "
        "system's cryptographically secure random source, so an attacker cannot predict "
        "future codes from past ones. The code is stored in the database with an expiry "
        "of 5 minutes (otp_expiry = current_time + 300 seconds)."
    )
    pdf.body(
        "Verification validates three properties: (a) an OTP actually exists for the "
        "pending user, (b) the current time has not passed otp_expiry, and (c) the "
        "submitted value matches the stored one. The match uses hmac.compare_digest(), "
        "a constant-time comparison that prevents timing side-channel attacks. A failed "
        "match decrements a limited attempt counter; after five wrong attempts the OTP "
        "is invalidated and the user must log in again, which throttles brute-force "
        "guessing of the 6-digit space."
    )

    pdf.h2("4.2 Password Hashing")
    pdf.body(
        "Passwords are never stored in plain text. At registration, "
        "generate_password_hash(password) produces a salted, one-way digest that is saved "
        "in password_hash. Werkzeug derives this using a deliberately slow key-derivation "
        "function (scrypt / PBKDF2 with a random salt per user). The salt ensures that two "
        "users with the same password produce different hashes, and the slowness makes "
        "large-scale offline cracking expensive."
    )
    pdf.body(
        "At login, check_password_hash(stored_hash, supplied_password) recomputes the "
        "derivation with the stored salt and compares the result. The application only "
        "ever sees the plain-text password in memory during this request. Because the "
        "hash cannot be reversed, even a full database leak would not directly reveal "
        "users' passwords."
    )

    pdf.h2("4.3 Session Protection and Other Measures")
    for item in [
        "Only after both factors pass does the server set session['authenticated'] = True; "
        "every protected route is guarded by the @login_required decorator.",
        "The session cookie is HttpOnly and SameSite=Lax, reducing exposure to XSS and CSRF.",
        "Login failures use a generic error message so usernames cannot be enumerated.",
        "OTP codes are single-use and cleared from the database after verification or expiry.",
        "By default the OTP is delivered only to the account email and is not shown on the "
        "server screen; a demo mode can expose it in the terminal and testing banner.",
    ]:
        pdf.bullet(item)

    pdf.h2("4.4 Forgot-Password Flow")
    pdf.body(
        "The forgot-password flow is intentionally similar to login 2FA. The user "
        "submits the account email and the server generates a fresh 6-digit reset code "
        "using the same cryptographically secure generator. The code is stored in "
        "reset_code with reset_expiry set 15 minutes ahead, printed in the terminal, "
        "shown in a testing banner, and emailed when SMTP is configured."
    )
    pdf.body(
        "To complete the reset, the user must supply the correct code before it expires "
        "and choose a new password of at least 8 characters. The new password is hashed "
        "with generate_password_hash before storage, and both reset fields plus any "
        "pending login OTP are cleared in the same UPDATE. Five incorrect attempts "
        "invalidate the code. The forgot-password form always returns a generic message, "
        "which avoids revealing whether an email address is registered."
    )

    pdf.h2("4.5 Threat-to-Mitigation Summary")
    pdf.table(
        ["THREAT", "MITIGATION IN THIS SYSTEM"],
        [
            ["Stolen / guessed password", "Second factor (OTP) is still required"],
            ["Plain-text password leak", "Passwords stored as salted one-way hashes"],
            ["OTP brute force", "5-attempt limit and single-use codes"],
            ["Replay of an old OTP", "OTP + expiry cleared after use / after 300 s"],
            ["Predicting OTP values", "Cryptographically secure secrets module"],
            ["Direct access to dashboard", "@login_required session check on the route"],
        ],
        [58, 112],
    )

    # ---------------- 5. Code Snippets ----------------
    pdf.add_page()
    pdf.h1(5, "Key Code Snippets")
    pdf.body("The following excerpts illustrate the most important security-relevant parts of app.py.")

    pdf.h2("Password hashing at registration")
    pdf.code(
        "from werkzeug.security import generate_password_hash, check_password_hash\n\n"
        "password_hash = generate_password_hash(password)\n"
        "conn.execute(\n"
        "    'INSERT INTO users (username, email, password_hash) VALUES (?, ?, ?)',\n"
        "    (username, email, password_hash),\n"
        ")"
    )
    pdf.caption("Code snippet 2: a password is hashed before it reaches the database.")

    pdf.h2("Credential check and OTP generation at login")
    pdf.code(
        "if user and check_password_hash(user['password_hash'], password):\n"
        "    otp = str(secrets.randbelow(900000) + 100000)   # 6-digit OTP\n"
        "    expiry = int(time.time()) + 300                  # 5-minute validity\n"
        "    conn.execute(\n"
        "        'UPDATE users SET otp_code = ?, otp_expiry = ? WHERE id = ?',\n"
        "        (otp, expiry, user['id']),\n"
        "    )\n"
        "    print_otp_to_terminal(user['username'], otp)\n"
        "    return redirect(url_for('verify_2fa'))"
    )
    pdf.caption("Code snippet 3: after the first factor succeeds, the OTP is created, stored and printed.")

    pdf.h2("OTP verification (expiry + constant-time compare)")
    pdf.code(
        "if user['otp_expiry'] is None or user['otp_expiry'] < int(time.time()):\n"
        "    clear_otp(user_id)\n"
        "    flash('The OTP has expired. Please log in again.', 'danger')\n"
        "    return redirect(url_for('login'))\n\n"
        "if hmac.compare_digest(submitted, user['otp_code']):\n"
        "    clear_otp(user_id)\n"
        "    session.clear()\n"
        "    session['authenticated'] = True\n"
        "    session['user_id'] = user['id']\n"
        "    return redirect(url_for('dashboard'))"
    )
    pdf.caption("Code snippet 4: the second factor is validated before a session is created.")

    pdf.h2("Protected route decorator")
    pdf.code(
        "def login_required(view):\n"
        "    @wraps(view)\n"
        "    def wrapped(*args, **kwargs):\n"
        "        if not session.get('authenticated'):\n"
        "            flash('Please log in to access that page.', 'danger')\n"
        "            return redirect(url_for('login'))\n"
        "        return view(*args, **kwargs)\n"
        "    return wrapped\n\n"
        "@app.route('/dashboard')\n"
        "@login_required\n"
        "def dashboard():\n"
        "    ..."
    )
    pdf.caption("Code snippet 5: unauthenticated users cannot reach protected pages.")

    # ---------------- 6. Run Instructions ----------------
    pdf.add_page()
    pdf.h1(6, "Step-by-Step Instructions to Run the Project")
    pdf.numbered(1, "Open a terminal and change into the project folder:")
    pdf.code("cd /home/pc/secure_login_system")
    pdf.numbered(2, "Activate the included virtual environment:")
    pdf.code("source venv/bin/activate")
    pdf.numbered(3, "Install dependencies (only needed if the venv was not provided):")
    pdf.code("pip install -r requirements.txt")
    pdf.numbered(4, "Initialize the database (optional - the app does this automatically):")
    pdf.code("python init_db.py --seed")
    pdf.numbered(5, "Generate this PDF report:")
    pdf.code("python generate_report.py")
    pdf.numbered(6, "Start the Flask server:")
    pdf.code("python app.py")
    pdf.numbered(7, "Open a browser and go to http://127.0.0.1:5000")
    pdf.body("")
    pdf.h2("Testing the full flow")
    for item in [
        "Register a new account at /register, or use the seeded demo account "
        "(username: demo, password: Demo@1234).",
        "Submit the login form. The terminal prints a message similar to: "
        "'[2FA] OTP for user demo: 483920'.",
        "The browser redirects to /verify-2fa; the same OTP also appears in the yellow "
        "testing banner on that page.",
        "Type the 6 digits and click Verify. A successful check opens /dashboard.",
        "Try an expired or wrong OTP to observe the error handling and attempt counter.",
        "Click Logout to clear the session and confirm /dashboard is protected.",
    ]:
        pdf.bullet(item)
    pdf.ln(2)
    pdf.h2("Optional: Email Delivery of the OTP")
    pdf.body(
        "By default OTP_DELIVERY=email: the code is sent only to the address on the "
        "account and is never printed in the terminal or shown on screen. Generate a "
        "Gmail App Password, then place GMAIL_ADDRESS and GMAIL_APP_PASSWORD in the "
        "local .env file (loaded automatically and ignored by git). Login is blocked with "
        "a clear message until credentials are present. Setting OTP_DELIVERY=demo "
        "restores the terminal/testing-banner fallback. Credentials are never stored in "
        "the source code or the database."
    )
    pdf.code(
        "export GMAIL_ADDRESS=kanu6a6y@gmail.com\n"
        "export GMAIL_APP_PASSWORD='your-16-character-app-password'\n"
        "python test_email.py\n"
        "python app.py"
    )
    pdf.body(
        "If no email arrives, run 'python test_email.py'. It reports whether the "
        "environment variables are visible to the process and whether Gmail accepted the "
        "app password. A normal Google password will not work - Gmail requires a "
        "16-character App Password with 2-Step Verification enabled. The terminal and "
        "testing banner always display the code as a fallback."
    )
    pdf.h2("Route Summary")
    pdf.table(
        ["ROUTE", "METHOD", "DESCRIPTION"],
        [
            ["/register", "GET / POST", "Create a new user account"],
            ["/login", "GET / POST", "Verify password, issue OTP"],
            ["/verify-2fa", "GET / POST", "Verify the 6-digit OTP"],
            ["/resend-otp", "POST", "Generate a replacement OTP"],
            ["/forgot-password", "GET / POST", "Request a password reset code"],
            ["/reset-password", "GET / POST", "Enter reset code and new password"],
            ["/resend-reset", "POST", "Generate a replacement reset code"],
            ["/dashboard", "GET", "Protected user dashboard"],
            ["/logout", "GET", "End the session"],
        ],
        [40, 34, 96],
    )

    # ---------------- 7. Conclusion ----------------
    pdf.add_page()
    pdf.h1(7, "Conclusion")
    pdf.body(
        "This assignment delivers a complete, runnable Secure Login System that combines "
        "a local SQLite database with two strong, complementary defenses: salted password "
        "hashing and time-limited, cryptographically random one-time passwords. The design "
        "ensures that a password alone is never enough to gain access, that plain-text "
        "passwords are never persisted, and that OTPs cannot be reused or guessed "
        "practically."
    )
    pdf.body(
        "Because SQLite is embedded in Python and the OTP is delivered through the terminal "
        "and an on-page testing banner, the whole project runs immediately with no external "
        "database, mail, or SMS services. The automatically generated Assignment_Report.pdf "
        "documents the architecture, database, security analysis, code, and run steps - "
        "making it suitable for submission and demonstration."
    )
    pdf.ln(6)
    pdf.set_font("Helvetica", "I", 9)
    pdf.set_text_color(*MUTED)
    pdf.multi_cell(0, 6, "End of report - Secure Login System, {}.".format(date.today().strftime("%B %d, %Y")),
                   align="C", new_x=XPos.LMARGIN, new_y=YPos.NEXT)

    pdf.output(OUTPUT)
    print("PDF report generated successfully: {}".format(OUTPUT))


if __name__ == "__main__":
    build_report()
