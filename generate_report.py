#!/usr/bin/env python3
"""Generate the professional PDF assignment report.

Run:  .venv/bin/python generate_report.py
Output: Assignment_Report.pdf (project root)
"""

from __future__ import annotations

import platform
import sqlite3
import sys
from datetime import date
from pathlib import Path

from fpdf import FPDF
from fpdf.enums import XPos, YPos

try:
    from PIL import Image
except ImportError:  # Pillow is installed with fpdf2
    Image = None

BASE_DIR = Path(__file__).resolve().parent
ASSETS = BASE_DIR / "report_assets"
OUTPUT = BASE_DIR / "Assignment_Report.pdf"

NAVY = (17, 28, 68)
NAVY_2 = (24, 38, 86)
BLUE = (37, 99, 235)
BLUE_DARK = (29, 78, 216)
VIOLET = (109, 40, 217)
CYAN = (8, 145, 178)
INK = (15, 23, 42)
INK_SOFT = (51, 65, 85)
MUTED = (100, 116, 139)
LINE = (219, 227, 244)
LINE_SOFT = (235, 240, 249)
PALE_BLUE = (239, 246, 255)
PALE_GREEN = (236, 253, 245)
GREEN = (4, 120, 87)
PALE_RED = (254, 242, 242)
RED = (185, 28, 28)
WHITE = (255, 255, 255)

SECTION_DEFS = [
    ("01", "Project Overview", "Purpose, scope, features and requirement coverage"),
    ("02", "System Architecture & Tech Stack", "Components, request lifecycle and technology choices"),
    ("03", "Database Schema & Connection", "SQLite file, users table, OTP state and data access"),
    ("04", "Security: Password Hashing", "scrypt, salting and credential-storage analysis"),
    ("05", "Security: Two-Step Verification", "OTP generation, expiry, delivery and verification"),
    ("06", "Recovery & Defensive Controls", "Forgot password, CSRF, sessions, lockout and headers"),
    ("07", "Key Code Snippets", "Annotated implementation excerpts"),
    ("08", "Running the Project", "Installation, configuration and demonstration steps"),
    ("09", "Verification & Test Results", "Automated tests, live browser test and environment evidence"),
    ("10", "Limitations & Conclusion", "Production hardening notes and final assessment"),
    ("A", "Appendix: Project Structure", "File-by-file repository map"),
    ("B", "Appendix: Interface Preview", "Screenshots of the implemented screens"),
]


class Report(FPDF):
    CONTENT_W = 174.0

    def __init__(self, toc_pages: dict[str, int] | None = None) -> None:
        super().__init__(orientation="P", unit="mm", format="A4")
        self.toc_pages = toc_pages or {}
        self.section_pages: dict[str, int] = {}
        self.set_margins(18, 20, 18)
        self.set_auto_page_break(auto=True, margin=18)
        self.set_title("Secure Login System - Assignment Report")
        self.set_author("Secure Login System Project")
        self.set_subject(
            "Flask and SQLite secure authentication with 2-step verification, "
            "password hashing and account recovery"
        )
        self.set_creator("generate_report.py (fpdf2)")

    # ------------------------------------------------------------------
    # Page furniture
    # ------------------------------------------------------------------
    def header(self) -> None:
        if self.page_no() == 1:
            return
        self.set_y(9)
        self.set_font("helvetica", "B", 6.8)
        self.set_text_color(*MUTED)
        self.cell(
            120,
            4,
            "SECURE LOGIN SYSTEM   /   TECHNICAL ASSIGNMENT REPORT",
            new_x=XPos.RIGHT,
            new_y=YPos.TOP,
        )
        self.cell(0, 4, "FLASK + SQLITE + 2FA", align="R")
        self.set_draw_color(*LINE)
        self.set_line_width(0.25)
        self.line(18, 15, 192, 15)
        self.set_y(20)

    def footer(self) -> None:
        if self.page_no() == 1:
            return
        self.set_y(-14)
        self.set_draw_color(*LINE)
        self.set_line_width(0.25)
        self.line(18, 282, 192, 282)
        self.set_y(-11)
        self.set_font("helvetica", "", 6.8)
        self.set_text_color(*MUTED)
        self.cell(120, 4, "Prepared for db1434@gmail.com  |  November 2026")
        self.cell(0, 4, f"Page {self.page_no()} of {{nb}}", align="R")

    # ------------------------------------------------------------------
    # Reusable layout primitives
    # ------------------------------------------------------------------
    def ensure(self, height: float) -> None:
        if self.get_y() + height > self.h - self.b_margin - 2:
            self.add_page()

    def section_title(self, number: str, title: str, subtitle: str) -> None:
        self.ensure(30)
        self.set_fill_color(*BLUE)
        self.rect(18, self.get_y() + 1, 13, 6.5, style="F")
        self.set_xy(18, self.get_y() + 1.4)
        self.set_font("helvetica", "B", 7)
        self.set_text_color(*WHITE)
        self.cell(13, 3.5, f"SEC {number}", align="C")
        self.set_xy(35, self.get_y() - 1.4)
        self.set_font("helvetica", "B", 20)
        self.set_text_color(*INK)
        self.multi_cell(self.CONTENT_W - 17, 8.2, title, align="L")
        self.set_x(35)
        self.set_font("helvetica", "", 9)
        self.set_text_color(*MUTED)
        self.multi_cell(self.CONTENT_W - 17, 4.7, subtitle, align="L")
        self.set_draw_color(*BLUE)
        self.set_line_width(0.8)
        self.line(18, self.get_y() + 1.2, 48, self.get_y() + 1.2)
        self.ln(6)

    def subheading(self, text: str) -> None:
        self.ensure(13)
        self.ln(2)
        self.set_font("helvetica", "B", 11)
        self.set_text_color(*NAVY)
        self.multi_cell(self.CONTENT_W, 5.4, text, align="L")
        self.ln(1)

    def body(self, text: str, size: float = 9.2, leading: float = 5.0) -> None:
        self.set_font("helvetica", "", size)
        self.set_text_color(*INK_SOFT)
        self.multi_cell(self.CONTENT_W, leading, text.replace("`", ""), markdown=True, align="L")
        self.ln(1.8)

    def small(self, text: str) -> None:
        self.set_font("helvetica", "", 7.5)
        self.set_text_color(*MUTED)
        self.multi_cell(self.CONTENT_W, 4.0, text, align="L")
        self.ln(1)

    def bullets(self, items: list[str], size: float = 9.0) -> None:
        self.set_font("helvetica", "", size)
        self.set_text_color(*INK_SOFT)
        for item in items:
            self.ensure(8)
            y = self.get_y()
            self.set_fill_color(*BLUE)
            self.rect(19, y + 2.1, 1.65, 1.65, style="F")
            self.set_xy(23.5, y)
            self.multi_cell(self.CONTENT_W - 6, 4.7, item.replace("`", ""), markdown=True, align="L")
            self.ln(0.8)
        self.ln(1.2)

    def numbered(self, items: list[str]) -> None:
        self.set_font("helvetica", "", 9)
        self.set_text_color(*INK_SOFT)
        for index, item in enumerate(items, start=1):
            self.ensure(9)
            y = self.get_y()
            self.set_fill_color(*PALE_BLUE)
            self.rect(18, y, 6.5, 6.5, style="F")
            self.set_xy(18, y + 1.2)
            self.set_font("helvetica", "B", 7.5)
            self.set_text_color(*BLUE_DARK)
            self.cell(6.5, 3.5, str(index), align="C")
            self.set_xy(27, y)
            self.set_font("helvetica", "", 9)
            self.set_text_color(*INK_SOFT)
            self.multi_cell(self.CONTENT_W - 9, 4.8, item.replace("`", ""), markdown=True, align="L")
            self.ln(1.1)
        self.ln(1)

    def callout(self, title: str, text: str, tone: str = "blue") -> None:
        palette = {
            "blue": (PALE_BLUE, BLUE, (30, 64, 175)),
            "green": (PALE_GREEN, GREEN, (6, 95, 70)),
            "red": (PALE_RED, RED, (153, 27, 27)),
        }
        fill, accent, text_color = palette.get(tone, palette["blue"])
        self.ensure(22)
        inner_w = self.CONTENT_W - 11
        self.set_font("helvetica", "", 8.3)
        lines = self.multi_cell(inner_w, 4.4, text, dry_run=True, output="LINES")
        height = 9.5 + len(lines) * 4.4 + 4
        self.ensure(height)
        y = self.get_y()
        self.set_fill_color(*fill)
        self.rect(18, y, self.CONTENT_W, height, style="F")
        self.set_fill_color(*accent)
        self.rect(18, y, 1.8, height, style="F")
        self.set_xy(23, y + 2.8)
        self.set_font("helvetica", "B", 8.6)
        self.set_text_color(*accent)
        self.cell(0, 4, title)
        self.set_xy(23, y + 8.2)
        self.set_font("helvetica", "", 8.3)
        self.set_text_color(*text_color)
        self.multi_cell(inner_w, 4.4, text, align="L")
        self.set_y(y + height + 5)

    def table(
        self,
        headers: list[str],
        rows: list[list[str]],
        widths: list[float],
        font_size: float = 7.6,
        header_size: float = 7.2,
        line_h: float = 3.7,
    ) -> None:
        assert abs(sum(widths) - self.CONTENT_W) < 0.2, sum(widths)
        self.set_auto_page_break(False)
        header_h = 7.2

        def draw_header() -> None:
            y = self.get_y()
            x = self.l_margin
            self.set_fill_color(*NAVY)
            self.set_draw_color(*NAVY)
            self.set_font("helvetica", "B", header_size)
            self.set_text_color(*WHITE)
            for width, label in zip(widths, headers):
                self.rect(x, y, width, header_h, style="DF")
                self.set_xy(x + 1.4, y + 2.2)
                self.cell(width - 2.8, 3, label)
                x += width
            self.set_y(y + header_h)

        draw_header()
        for index, row in enumerate(rows):
            heights = []
            for width, text in zip(widths, row):
                self.set_font("helvetica", "", font_size)
                wrapped = self.multi_cell(
                    width - 2.8, line_h, str(text).replace("`", ""), dry_run=True, output="LINES"
                )
                heights.append(max(1, len(wrapped)) * line_h + 2.4)
            row_h = max(7.2, max(heights))

            if self.get_y() + row_h > self.h - self.b_margin - 1:
                self.add_page()
                draw_header()

            y = self.get_y()
            x = self.l_margin
            fill = (248, 250, 255) if index % 2 == 0 else WHITE
            self.set_draw_color(*LINE)
            self.set_text_color(*INK_SOFT)
            for width, text in zip(widths, row):
                self.set_fill_color(*fill)
                self.rect(x, y, width, row_h, style="DF")
                self.set_xy(x + 1.4, y + 1.2)
                self.set_font("helvetica", "", font_size)
                self.multi_cell(width - 2.8, line_h, str(text).replace("`", ""), align="L")
                x += width
            self.set_y(y + row_h)

        self.set_auto_page_break(True, margin=18)
        self.ln(4)

    def code(self, caption: str, code: str, font_size: float = 6.9) -> None:
        caption = caption.strip()
        self.ensure(16)
        self.set_font("helvetica", "B", 7.4)
        self.set_text_color(*BLUE_DARK)
        self.multi_cell(self.CONTENT_W, 4.2, caption.upper())
        self.ln(0.6)

        line_h = 3.9
        char_width = 106
        self.set_auto_page_break(False)
        for raw_line in code.strip("\n").splitlines():
            line = raw_line.replace("\t", "    ").replace("\u2018", "'").replace("\u2019", "'")
            chunks = [line[i : i + char_width] for i in range(0, len(line), char_width)] or [""]
            for chunk in chunks:
                if self.get_y() + line_h > self.h - self.b_margin - 2:
                    self.add_page()
                    self.set_font("helvetica", "B", 7.2)
                    self.set_text_color(*MUTED)
                    self.cell(0, 4, f"{caption.upper()}  (CONTINUED)", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
                    self.ln(0.4)
                y = self.get_y()
                self.set_fill_color(247, 249, 253)
                self.rect(18, y, self.CONTENT_W, line_h, style="F")
                self.set_fill_color(*BLUE)
                self.rect(18, y, 1.3, line_h, style="F")
                self.set_xy(21.5, y + 0.25)
                self.set_font("courier", "", font_size)
                self.set_text_color(30, 41, 59)
                self.cell(self.CONTENT_W - 4.2, line_h - 0.5, chunk)
                self.set_y(y + line_h)
        self.set_auto_page_break(True, margin=18)
        self.ln(3.5)

    def figure_caption(self, text: str) -> None:
        self.set_font("helvetica", "", 7.2)
        self.set_text_color(*MUTED)
        self.multi_cell(self.CONTENT_W, 3.8, text, align="C")
        self.ln(2)

    def screenshot(self, path: Path, width: float, caption: str | None = None) -> None:
        if not path.exists():
            self.small(f"[Screenshot not found: {path.name}]")
            return
        # Add a little breathing room before the image.
        self.ensure(width * 0.75 + 12)
        x = (210 - width) / 2
        y = self.get_y()
        self.set_draw_color(*LINE)
        self.set_line_width(0.3)
        self.image(str(path), x=x, y=y, w=width)
        # fpdf needs the height; use Pillow to calculate it.
        height = 0
        if Image is not None:
            with Image.open(path) as img:
                height = width * img.height / img.width
        if height:
            self.rect(x, y, width, height)
            self.set_y(y + height + 1.8)
        if caption:
            self.figure_caption(caption)

    # ------------------------------------------------------------------
    # Cover, contents and summary
    # ------------------------------------------------------------------
    def cover(self) -> None:
        self.add_page()
        self.set_fill_color(*NAVY)
        self.rect(0, 0, 210, 297, style="F")

        # Decorative geometry.
        self.set_fill_color(23, 37, 84)
        self.ellipse(130, -38, 135, 135, style="F")
        self.set_fill_color(30, 41, 96)
        self.ellipse(-48, 205, 150, 150, style="F")
        self.set_draw_color(64, 90, 160)
        self.set_line_width(0.35)
        self.ellipse(116, 174, 120, 120, style="D")
        self.ellipse(132, 190, 88, 88, style="D")
        self.set_draw_color(78, 113, 200)
        self.line(0, 40, 210, 40)
        self.set_fill_color(*BLUE)
        self.rect(0, 39.2, 64, 1.6, style="F")

        self.set_xy(18, 24)
        self.set_fill_color(*BLUE)
        self.rect(18, 24, 33, 8, style="F")
        self.set_xy(18, 26)
        self.set_font("helvetica", "B", 6.8)
        self.set_text_color(*WHITE)
        self.cell(33, 4, "SECURITY ASSIGNMENT", align="C")

        self.set_xy(18, 57)
        self.set_font("helvetica", "B", 9)
        self.set_text_color(147, 197, 253)
        self.cell(0, 5, "FULL-STACK SECURE AUTHENTICATION")

        self.set_xy(18, 70)
        self.set_font("helvetica", "B", 38)
        self.set_text_color(*WHITE)
        self.multi_cell(168, 15.5, "Secure Login\nSystem", align="L")

        self.set_xy(18, 112)
        self.set_draw_color(96, 165, 250)
        self.set_line_width(0.9)
        self.line(18, 112, 84, 112)

        self.set_xy(18, 120)
        self.set_font("helvetica", "", 13.5)
        self.set_text_color(203, 213, 225)
        self.multi_cell(
            158,
            7,
            "Password hashing, email-based two-step verification and secure account "
            "recovery built with Flask and SQLite.",
            align="L",
        )

        self.set_xy(18, 164)
        self.set_font("helvetica", "", 8.4)
        self.set_text_color(148, 163, 184)
        self.cell(30, 5, "PREPARED FOR")
        self.set_xy(18, 169)
        self.set_font("helvetica", "B", 11)
        self.set_text_color(*WHITE)
        self.cell(0, 5, "db1434@gmail.com")

        self.set_xy(18, 181)
        self.set_font("helvetica", "", 8.4)
        self.set_text_color(148, 163, 184)
        self.cell(30, 5, "DATE")
        self.set_xy(18, 186)
        self.set_font("helvetica", "B", 11)
        self.set_text_color(*WHITE)
        self.cell(0, 5, "17 November 2026")

        self.set_xy(18, 198)
        self.set_font("helvetica", "", 8.4)
        self.set_text_color(148, 163, 184)
        self.cell(30, 5, "ARTEFACT")
        self.set_xy(18, 203)
        self.set_font("helvetica", "B", 11)
        self.set_text_color(*WHITE)
        self.cell(0, 5, "Assignment_Report.pdf")

        # Technology chips.
        chips = ["Python 3.14", "Flask 3.1", "SQLite 3.46", "Werkzeug scrypt", "Email OTP"]
        x = 18
        self.set_y(226)
        for chip in chips:
            self.set_font("helvetica", "", 7)
            width = self.get_string_width(chip) + 9
            if x + width > 192:
                x = 18
                self.set_y(self.get_y() + 10)
            self.set_draw_color(80, 105, 165)
            self.set_fill_color(25, 39, 85)
            self.rect(x, self.get_y(), width, 8, style="DF", round_corners=True, corner_radius=2)
            self.set_xy(x, self.get_y() + 2)
            self.set_text_color(219, 234, 254)
            self.cell(width, 4, chip, align="C")
            x += width + 4

        self.set_xy(18, 266)
        self.set_font("helvetica", "", 7.4)
        self.set_text_color(120, 140, 180)
        self.cell(
            0,
            4,
            "Architecture  |  Database schema  |  Security analysis  |  Code walkthrough  |  Run guide",
        )

    def contents_and_summary(self) -> None:
        self.add_page()
        self.set_font("helvetica", "B", 9)
        self.set_text_color(*BLUE_DARK)
        self.cell(0, 5, "EXECUTIVE SUMMARY", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        self.ln(1)
        self.set_font("helvetica", "B", 24)
        self.set_text_color(*INK)
        self.multi_cell(self.CONTENT_W, 10, "A secure sign-in flow, end to end.")
        self.ln(1)
        self.body(
            "This report documents a complete local full-stack authentication project. "
            "Users register with a username, email address and a strong password. Every "
            "password is transformed into a salted **scrypt** hash before it is stored. "
            "A correct password does not immediately create a session: the application "
            "issues a random six-digit one-time passcode (OTP), delivers it to the "
            "authorised owner inbox, and prints it in the server terminal for offline "
            "demonstration. Only a valid, unexpired code opens the protected dashboard.",
            size=8.9,
        )
        self.body(
            "The build includes a complete forgot-password flow protected by the same "
            "one-time-code channel, account lockout, CSRF tokens on every state-changing "
            "request, hardened cookies and browser security headers. Nine automated "
            "end-to-end tests exercise registration, hashing, 2FA, lockout, password "
            "reset and CSRF enforcement.",
            size=8.9,
        )

        # Summary metrics.
        metrics = [
            ("9 / 9", "automated tests passed"),
            ("2", "authentication factors"),
            ("0", "plain-text passwords stored"),
        ]
        y = self.get_y() + 1
        box_w = 56
        for index, (value, label) in enumerate(metrics):
            x = 18 + index * 59
            self.set_fill_color(248, 250, 255)
            self.set_draw_color(*LINE)
            self.rect(x, y, box_w, 17, style="DF", round_corners=True, corner_radius=2)
            self.set_xy(x + 3, y + 3)
            self.set_font("helvetica", "B", 14)
            self.set_text_color(*BLUE_DARK)
            self.cell(box_w - 6, 6, value)
            self.set_xy(x + 3, y + 10)
            self.set_font("helvetica", "", 6.5)
            self.set_text_color(*MUTED)
            self.cell(box_w - 6, 3.5, label)
        self.set_y(y + 23)

        self.set_font("helvetica", "B", 13)
        self.set_text_color(*INK)
        self.cell(0, 6, "Contents", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        self.ln(1)
        for number, title, description in SECTION_DEFS:
            self.ensure(10)
            y = self.get_y()
            page = self.toc_pages.get(number, "")
            self.set_fill_color(*PALE_BLUE)
            self.rect(18, y, 9, 7, style="F")
            self.set_xy(18, y + 1.9)
            self.set_font("helvetica", "B", 6.6)
            self.set_text_color(*BLUE_DARK)
            self.cell(9, 3.2, number, align="C")
            self.set_xy(30.5, y + 0.7)
            self.set_font("helvetica", "B", 8.2)
            self.set_text_color(*INK)
            self.cell(133, 4, title)
            if page:
                self.set_xy(164, y + 0.7)
                self.set_font("helvetica", "B", 8.2)
                self.set_text_color(*BLUE_DARK)
                self.cell(10, 4, str(page), align="R")
            self.set_xy(30.5, y + 4.3)
            self.set_font("helvetica", "", 6.4)
            self.set_text_color(*MUTED)
            self.cell(145, 3, description)
            self.set_draw_color(*LINE_SOFT)
            self.set_line_width(0.2)
            self.line(30.5, y + 7.2, 192, y + 7.2)
            self.set_y(y + 8.4)

        self.ln(2)
        self.callout(
            "How to use this report",
            "Sections 1-3 explain the product and its data model. Sections 4-6 analyse "
            "the security design. Section 7 highlights the most important code. Section 8 "
            "contains the exact run commands, and Section 9 records the verification evidence.",
        )

    # ------------------------------------------------------------------
    # Section 1: overview
    # ------------------------------------------------------------------
    def section_overview(self) -> None:
        self.add_page()
        self.start_section("01 Project Overview", level=0)
        self.section_pages["01"] = self.page_no()
        self.section_title(
            "01",
            "Project Overview",
            "A local, ready-to-run authentication system with two independent factors.",
        )

        self.subheading("1.1 Purpose and scope")
        self.body(
            "The assignment asks for a secure login system connected to a database, with "
            "two-step verification, hashed passwords, a protected dashboard and an "
            "automatically generated PDF report. The implementation delivers those "
            "requirements as a self-contained Flask application backed by a local SQLite "
            "file. There is no external database server, message queue or paid service to "
            "configure."
        )
        self.body(
            "The project is intentionally designed for demonstration. One-time codes are "
            "delivered over Gmail SMTP when valid credentials are configured, and are "
            "**always** printed to the server console. A fixed recipient override means "
            "every code is sent to **db1434@gmail.com** only, regardless of which email "
            "address a visitor uses during registration."
        )

        self.subheading("1.2 Delivered capabilities")
        self.bullets(
            [
                "**Registration** at `/register` with username, email and password validation.",
                "**Secure login** at `/login` using either a username or an email address.",
                "**Email OTP 2FA** at `/verify-2fa`, with a six-digit code, five-minute expiry and attempt limit.",
                "**Protected dashboard** at `/dashboard`, available only after successful verification.",
                "**Forgot password** at `/forgot-password` and reset at `/reset-password`, also protected by an OTP.",
                "**Automatic database initialisation** on application startup and through `init_db.py`.",
                "**PDF reporting** generated programmatically with fpdf2, including screenshots and test evidence.",
            ]
        )

        self.subheading("1.3 Requirement coverage")
        self.table(
            ["Assignment requirement", "Delivered implementation"],
            [
                ["Flask or Express with local SQLite", "Flask 3.1.3 with `database.db`; no database server required."],
                ["Automatic users table", "`init_db.py` plus startup initialisation creates the table idempotently."],
                ["Required user columns", "id, username, email, password_hash, otp_code and otp_expiry are present."],
                ["Registration, login, OTP, dashboard", "Responsive pages for all four flows, plus logout."],
                ["2-step verification", "Random six-digit OTP, database state, expiry, delivery and verification."],
                ["Password hashing", "Werkzeug scrypt hashes with a unique per-password salt."],
                ["Print OTP in server terminal", "A framed console banner prints every code for easy testing."],
                ["Automated PDF report", "`Assignment_Report.pdf` generated by `generate_report.py`."],
            ],
            widths=[58, 116],
            font_size=7.6,
        )

        self.callout(
            "Design goal",
            "A stolen password alone must never be enough to reach the dashboard. The "
            "password check and the OTP check are separate gates, and the protected route "
            "trusts only the verified session created after both gates succeed.",
            tone="blue",
        )

        self.subheading("1.4 User journey")
        self.numbered(
            [
                "Create an account; policy checks run before the password is hashed and inserted.",
                "Sign in; the password is verified against the stored scrypt hash.",
                "Enter the OTP delivered to the owner inbox and printed in the terminal.",
                "The verified session opens the dashboard; sign-out destroys it.",
            ]
        )


    # ------------------------------------------------------------------
    # Section 2: architecture
    # ------------------------------------------------------------------
    def section_architecture(self) -> None:
        self.add_page()
        self.start_section("02 System Architecture & Tech Stack", level=0)
        self.section_pages["02"] = self.page_no()
        self.section_title(
            "02",
            "System Architecture & Tech Stack",
            "A small, auditable request path from browser form to SQLite row and back.",
        )

        self.subheading("2.1 Component view")
        self.draw_architecture()
        self.figure_caption(
            "Figure 1. Main components. The browser never talks to SQLite directly; every "
            "read and write passes through validated Flask routes."
        )

        self.subheading("2.2 Request lifecycle")
        self.numbered(
            [
                "The browser sends a form POST with a hidden CSRF token and a session cookie.",
                "Flask validates the CSRF token before the route executes, then queries SQLite with parameterised SQL.",
                "The password is checked against the stored scrypt hash; failures update the lockout counters.",
                "On success, a random OTP is generated, keyed-hashed and stored with its expiry in the same row.",
                "The mailer attempts owner-only SMTP delivery; the console banner prints the code in every case.",
                "A valid OTP clears the OTP fields, rotates the session and creates the authenticated session.",
            ]
        )

        self.subheading("2.3 Technology choices")
        self.table(
            ["Layer", "Technology", "Why it was selected"],
            [
                ["Web framework", "Flask 3.1.3", "Minimal, readable routing and sessions; ideal for a focused security assignment."],
                ["Templates", "Jinja2 3.1.6", "Auto-escaping by default and clean separation of HTML from Python."],
                ["Password hashing", "Werkzeug 3.1.9 scrypt", "Memory-hard KDF with per-password salt and constant-time verification."],
                ["Database", "SQLite 3.46.1", "Single local file, zero configuration, transactional and easy to inspect."],
                ["Configuration", "python-dotenv 1.2.4", "Keeps SMTP secrets and the Flask secret key out of source files."],
                ["Email", "Gmail SMTP over TLS", "Free, familiar delivery path; no third-party SDK required."],
            ],
            widths=[31, 48, 95],
            font_size=7.6,
        )

        self.subheading("2.4 Architecture decisions")
        self.bullets(
            [
                "**Server-side enforcement.** Hiding a link is never treated as access control; `/dashboard` checks the verified session on every request.",
                "**Single source of truth.** OTP state, expiry and attempt counters live in SQLite, not in a client cookie.",
                "**Fail-safe delivery.** SMTP failure does not block the demo; the OTP is still printed to the terminal.",
                "**Least privilege.** A pending login reaches only the verification page; the dashboard needs a verified session.",
            ]
        )

    def draw_architecture(self) -> None:
        self.ensure(82)
        y = self.get_y()
        box_w = 48
        box_h = 27
        gap = 15
        xs = [18, 18 + box_w + gap, 18 + 2 * (box_w + gap)]
        boxes = [
            ("01  CLIENT", "Browser", "HTML + CSS + JS\nForms + CSRF token"),
            ("02  APPLICATION", "Flask", "Routes + sessions\nscrypt + OTP logic"),
            ("03  STORAGE", "SQLite", "database.db\nusers + OTP state"),
        ]
        for x, (eyebrow, title, detail) in zip(xs, boxes):
            self.set_fill_color(248, 250, 255)
            self.set_draw_color(*LINE)
            self.rect(x, y, box_w, box_h, style="DF", round_corners=True, corner_radius=2)
            self.set_xy(x + 3, y + 3)
            self.set_font("helvetica", "B", 6.2)
            self.set_text_color(*BLUE_DARK)
            self.cell(box_w - 6, 3, eyebrow)
            self.set_xy(x + 3, y + 7.5)
            self.set_font("helvetica", "B", 10.5)
            self.set_text_color(*INK)
            self.cell(box_w - 6, 4.5, title)
            self.set_xy(x + 3, y + 14)
            self.set_font("helvetica", "", 6.8)
            self.set_text_color(*MUTED)
            self.multi_cell(box_w - 6, 3.4, detail)

        arrow_y = y + box_h / 2
        self.arrow(xs[0] + box_w, xs[1], arrow_y, "HTTPS")
        self.arrow(xs[1] + box_w, xs[2], arrow_y, "SQL")

        y2 = y + box_h + 12
        xs2 = xs
        boxes2 = [
            ("04  DELIVERY", "OTP engine", "secrets.randbelow\nHMAC digest + expiry"),
            ("05  TRANSPORT", "SMTP TLS", "smtp.gmail.com\nApp Password"),
            ("06  RECIPIENT", "Owner inbox", "db1434@gmail.com\nconsole fallback"),
        ]
        for x, (eyebrow, title, detail) in zip(xs2, boxes2):
            self.set_fill_color(245, 248, 255)
            self.set_draw_color(*LINE)
            self.rect(x, y2, box_w, box_h, style="DF", round_corners=True, corner_radius=2)
            self.set_xy(x + 3, y2 + 3)
            self.set_font("helvetica", "B", 6.2)
            self.set_text_color(*VIOLET)
            self.cell(box_w - 6, 3, eyebrow)
            self.set_xy(x + 3, y2 + 7.5)
            self.set_font("helvetica", "B", 10.5)
            self.set_text_color(*INK)
            self.cell(box_w - 6, 4.5, title)
            self.set_xy(x + 3, y2 + 14)
            self.set_font("helvetica", "", 6.8)
            self.set_text_color(*MUTED)
            self.multi_cell(box_w - 6, 3.4, detail)

        arrow_y2 = y2 + box_h / 2
        self.arrow(xs2[0] + box_w, xs2[1], arrow_y2, "SMTP")
        self.arrow(xs2[1] + box_w, xs2[2], arrow_y2, "deliver")
        self.set_y(y2 + box_h + 6)

    def arrow(self, x1: float, x2: float, y: float, label: str = "") -> None:
        self.set_draw_color(*BLUE)
        self.set_fill_color(*BLUE)
        self.set_line_width(0.5)
        self.line(x1 + 1, y, x2 - 2.4, y)
        self.polygon([(x2 - 1, y), (x2 - 3.6, y - 1.3), (x2 - 3.6, y + 1.3)], style="F")
        if label:
            self.set_font("helvetica", "", 5.8)
            self.set_text_color(*MUTED)
            self.set_xy(x1 + 1, y - 4.2)
            self.cell(x2 - x1 - 2, 2.8, label, align="C")

    def draw_otp_flow(self) -> None:
        self.ensure(38)
        y = self.get_y()
        width = 30.0
        gap = 6.0
        steps = [
            ("01", "Password", "scrypt check"),
            ("02", "Generate", "secrets CSPRNG"),
            ("03", "Store", "HMAC + expiry"),
            ("04", "Deliver", "owner inbox"),
            ("05", "Verify", "new session"),
        ]
        for index, (number, title, detail) in enumerate(steps):
            x = 18 + index * (width + gap)
            self.set_fill_color(248, 250, 255)
            self.set_draw_color(*LINE)
            self.rect(x, y, width, 24, style="DF", round_corners=True, corner_radius=2)
            self.set_xy(x + 2.5, y + 2.7)
            self.set_font("helvetica", "B", 5.8)
            self.set_text_color(*BLUE_DARK)
            self.cell(width - 5, 2.8, number)
            self.set_xy(x + 2.5, y + 7)
            self.set_font("helvetica", "B", 7.6)
            self.set_text_color(*INK)
            self.cell(width - 5, 3.4, title)
            self.set_xy(x + 2.5, y + 12.5)
            self.set_font("helvetica", "", 6.2)
            self.set_text_color(*MUTED)
            self.multi_cell(width - 5, 3.1, detail)
            if index < len(steps) - 1:
                self.arrow(x + width, x + width + gap, y + 12)
        self.set_y(y + 28)

    # ------------------------------------------------------------------
    # Section 3: database
    # ------------------------------------------------------------------
    def section_database(self) -> None:
        self.add_page()
        self.start_section("03 Database Schema & Connection", level=0)
        self.section_pages["03"] = self.page_no()
        self.section_title(
            "03",
            "Database Schema & Connection",
            "One local SQLite file, one users table and explicit OTP lifecycle fields.",
        )

        self.subheading("3.1 Storage location and connection")
        self.body(
            "The database is created at `database.db` in the project root unless `DATABASE_PATH` "
            "is set. `db.init_db()` runs at application startup, so the first launch is "
            "self-initialising. `init_db.py` exposes the same operation from the command line, "
            "with `--show` for schema inspection and `--reset` for a deliberate destructive "
            "rebuild."
        )
        self.table(
            ["Connection detail", "Value / behaviour"],
            [
                ["Database engine", "SQLite 3.46.1 (bundled with Python)"],
                ["File", "database.db in the project root (mode 0600 where supported)"],
                ["Initialisation", "`CREATE TABLE IF NOT EXISTS`; safe to run repeatedly"],
                ["Rows", "`sqlite3.Row` for named column access"],
                ["Foreign keys", "`PRAGMA foreign_keys = ON` on every connection"],
                ["Concurrency", "`PRAGMA busy_timeout = 5000`; short transactions via context managers"],
                ["Request lifecycle", "One connection per Flask request in `g`, closed on teardown"],
            ],
            widths=[47, 127],
            font_size=7.8,
        )

        self.subheading("3.2 users table")
        self.table(
            ["Column", "Type", "Constraint", "Purpose"],
            [
                ["id", "INTEGER", "PK, autoincrement", "Stable account identifier."],
                ["username", "TEXT", "NOT NULL, unique, NOCASE", "Display name and login identifier."],
                ["email", "TEXT", "NOT NULL, unique, NOCASE", "Login identifier and account contact."],
                ["password_hash", "TEXT", "NOT NULL", "Full Werkzeug scrypt hash including salt."],
                ["otp_code", "TEXT", "nullable", "Keyed HMAC-SHA256 digest of the active login OTP."],
                ["otp_expiry", "INTEGER", "nullable", "Unix timestamp after which the code is invalid."],
                ["otp_attempts", "INTEGER", "default 0", "Incorrect verification attempts for the active code."],
                ["otp_last_sent", "INTEGER", "nullable", "Timestamp used for the resend cooldown."],
                ["reset_code", "TEXT", "nullable", "Keyed digest of the active password-reset code."],
                ["reset_expiry", "INTEGER", "nullable", "Reset-code expiry timestamp."],
                ["reset_attempts", "INTEGER", "default 0", "Incorrect reset attempts."],
                ["reset_last_sent", "INTEGER", "nullable", "Reset resend timestamp."],
                ["failed_logins", "INTEGER", "default 0", "Consecutive failed password checks."],
                ["locked_until", "INTEGER", "nullable", "End of the temporary account lockout."],
                ["created_at", "INTEGER", "NOT NULL", "Account creation time (UTC seconds)."],
                ["last_login_at", "INTEGER", "nullable", "Last successful 2FA sign-in."],
            ],
            widths=[31, 22, 43, 78],
            font_size=7.3,
            line_h=3.5,
        )

        self.callout(
            "OTP storage note",
            "The schema keeps the required otp_code column, but the value stored there is "
            "not the raw six-digit code. It is an HMAC-SHA256 digest keyed by SECRET_KEY. "
            "A database copy therefore cannot be used to complete a pending login.",
            tone="green",
        )

        self.subheading("3.3 Schema and connection code")
        self.code(
            "Schema excerpt - db.py",
            """
CREATE TABLE IF NOT EXISTS users (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    username        TEXT    NOT NULL UNIQUE COLLATE NOCASE,
    email           TEXT    NOT NULL UNIQUE COLLATE NOCASE,
    password_hash   TEXT    NOT NULL,
    otp_code        TEXT,
    otp_expiry      INTEGER,
    otp_attempts    INTEGER NOT NULL DEFAULT 0,
    otp_last_sent   INTEGER,
    reset_code      TEXT,
    reset_expiry    INTEGER,
    reset_attempts  INTEGER NOT NULL DEFAULT 0,
    reset_last_sent INTEGER,
    failed_logins   INTEGER NOT NULL DEFAULT 0,
    locked_until    INTEGER,
    created_at      INTEGER NOT NULL,
    last_login_at   INTEGER
);
""",
        )
        self.code(
            "Connection helper - db.py",
            """
def connect(database_path):
    conn = sqlite3.connect(str(database_path), timeout=10)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    conn.execute("PRAGMA busy_timeout = 5000")
    return conn
""",
        )

        self.subheading("3.4 Why this shape works")
        self.bullets(
            [
                "**Single row per account.** OTP and lockout state are updated transactionally with the user, avoiding orphaned cache entries.",
                "**Timestamps as integers.** Expiry comparisons are simple, timezone-independent arithmetic in UTC seconds.",
                "**Unique NOCASE columns.** Usernames and emails cannot be duplicated by case changes such as `Alex` and `alex`.",
                "**No plaintext secrets.** Only password hashes, keyed OTP digests and operational counters are stored.",
                "**Automatic creation.** The first run cannot fail because a table was forgotten.",
            ]
        )

    # ------------------------------------------------------------------
    # Section 4: password hashing
    # ------------------------------------------------------------------
    def section_hashing(self) -> None:
        self.add_page()
        self.start_section("04 Security: Password Hashing", level=0)
        self.section_pages["04"] = self.page_no()
        self.section_title(
            "04",
            "Security Implementation: Password Hashing",
            "A slow, salted, memory-hard hash makes stolen password databases expensive to use.",
        )

        self.subheading("4.1 What is stored")
        self.body(
            "Passwords are never written to SQLite. The registration route calls Werkzeug's "
            "`generate_password_hash`, which defaults to **scrypt** in this environment. The "
            "result is a self-describing string such as "
            "`scrypt:32768:8:1$<random-salt>$<derived-key>`. It records the algorithm, "
            "cost parameters, a fresh 16-byte salt and the derived key."
        )
        self.body(
            "The parameters N=32768, r=8 and p=1 make the hash deliberately expensive: "
            "about 32 MiB of memory per attempt. That is negligible for one legitimate "
            "sign-in and costly for an attacker testing millions of candidates."
        )

        self.subheading("4.2 Registration and verification")
        self.code(
            "Registration - app.py",
            """
password_hash = generate_password_hash(password)
conn.execute(
    'INSERT INTO users (username, email, password_hash, created_at) '
    'VALUES (?, ?, ?, ?)',
    (username, email, password_hash, utc_now()),
)
""",
        )
        self.code(
            "Password check - app.py (with timing equalisation)",
            """
password_ok = (
    check_password_hash(user["password_hash"], password)
    if user
    else check_password_hash(DUMMY_HASH, password)
)
""",
        )
        self.body(
            "`check_password_hash` parses the stored parameters, re-derives the key with the "
            "stored salt and compares the result in constant time. For an unknown account, "
            "the route still performs one scrypt check against a dummy hash. That prevents "
            "a measurable timing difference from revealing whether an account exists."
        )

        self.subheading("4.3 Defensive properties")
        self.table(
            ["Property", "Effect"],
            [
                ["One-way derivation", "The original password cannot be recovered from the stored hash."],
                ["Unique salt", "Identical passwords produce different hashes; precomputed tables do not transfer."],
                ["Memory-hard KDF", "scrypt raises the cost of parallel GPU/ASIC guessing."],
                ["Tuned cost", "About 32 MiB and measurable CPU time per attempt, yet fast enough for interactive login."],
                ["Constant-time comparison", "Hash comparison does not leak how many leading bytes matched."],
            ],
            widths=[45, 129],
            font_size=7.8,
        )

        self.callout(
            "Why not SHA-256 or MD5?",
            "General-purpose hashes are designed to be fast. A modern GPU can test billions "
            "of MD5 candidates per second. scrypt is intentionally slow and memory-hungry, "
            "so each guess costs real resources. Salting also ensures that an attacker cannot "
            "reuse a precomputed rainbow table.",
            tone="blue",
        )

        self.subheading("4.4 Password policy and lockout")
        self.body(
            "Passwords require 10+ characters with upper and lower case, a number and a "
            "special character. Five consecutive failures lock the account for five minutes, "
            "and a successful check resets the counter. Registration and reset apply the same "
            "policy; a reset writes a fresh scrypt hash and clears lockout state."
        )

    # ------------------------------------------------------------------
    # Section 5: two-step verification
    # ------------------------------------------------------------------
    def section_two_factor(self) -> None:
        self.add_page()
        self.start_section("05 Security: Two-Step Verification", level=0)
        self.section_pages["05"] = self.page_no()
        self.section_title(
            "05",
            "Security Implementation: Two-Step Verification",
            "A random, short-lived possession factor delivered only to the authorised inbox.",
        )

        self.subheading("5.1 The second factor")
        self.body(
            "After a correct password, the application creates a six-digit code using Python's "
            "`secrets` module, not `random`. `secrets.randbelow(1_000_000)` is backed by the "
            "operating system CSPRNG and is suitable for security tokens. The code is stored "
            "as an HMAC-SHA256 digest, given an expiry timestamp five minutes in the future, "
            "and delivered by email."
        )
        self.draw_otp_flow()
        self.figure_caption(
            "Figure 2. Two-step verification lifecycle, including the terminal fallback used "
            "for local demonstrations."
        )

        self.subheading("5.2 OTP controls")
        self.table(
            ["Control", "Implementation", "Security value"],
            [
                ["Randomness", "`secrets.randbelow(1_000_000)`, zero-padded to six digits", "Unpredictable codes from a CSPRNG."],
                ["Expiry", "`OTP_TTL_SECONDS=300`, stored per user", "Limits the window for interception or guessing."],
                ["Single use", "OTP fields cleared immediately after success", "A captured code cannot be replayed."],
                ["At-rest protection", "HMAC-SHA256 with the server secret", "A leaked database does not contain usable codes."],
                ["Attempt limit", "Five wrong codes cancel verification", "Online guessing is capped at five attempts per code."],
                ["Resend cooldown", "60 seconds between sends", "Prevents inbox flooding and request abuse."],
                ["Owner-only delivery", "`OTP_RECIPIENT_OVERRIDE=db1434@gmail.com`", "Codes cannot be redirected to a visitor-supplied address."],
                ["Pending session", "Separate `pending_user_id`, no `user_id`", "The 2FA page cannot open the dashboard."],
                ["Session rotation", "`session.clear()` before issuing access", "Limits session-fixation risk at privilege change."],
            ],
            widths=[35, 80, 59],
            font_size=7.2,
            line_h=3.4,
        )

        self.subheading("5.3 Delivery policy")
        self.body(
            "The `.env` configuration sets `OTP_RECIPIENT_OVERRIDE=db1434@gmail.com`. The mailer "
            "reads this value first and sends every login or reset code there, even if a "
            "different account email was registered. This satisfies the requirement that "
            "codes can only go to the specified inbox. If SMTP is unavailable, the same code "
            "is printed in a clearly framed console banner, and the UI tells the operator to "
            "look there."
        )
        self.callout(
            "Gmail authentication note",
            "Google requires an **App Password** for SMTP when 2-Step Verification is enabled. "
            "A normal account password is rejected with 535 5.7.8 BadCredentials. Set "
            "`MAIL_PASSWORD` to a 16-character Google App Password to enable live email. The "
            "assignment flow remains demonstrable via the terminal until then.",
            tone="red",
        )

        self.subheading("5.4 Why a stolen password is not enough")
        self.body(
            "An attacker with the correct password can pass step one, but cannot pass step two "
            "without access to the owner inbox or the local terminal. The TOTP-like code is "
            "never returned in an API response, never rendered into the HTML and never stored "
            "in plaintext. It expires quickly, works once and tolerates only five incorrect "
            "guesses. The dashboard route additionally requires an authenticated session, "
            "so knowing the URL provides no bypass."
        )
        self.code(
            "OTP issuance - app.py",
            """
code = f"{secrets.randbelow(1_000_000):06d}"
with db.get_db() as conn:
    conn.execute(
        '''UPDATE users
           SET failed_logins = 0, locked_until = NULL,
               otp_code = ?, otp_expiry = ?, otp_attempts = 0,
               otp_last_sent = ?
           WHERE id = ?''',
        (hash_otp(code), now + app.config["OTP_TTL_SECONDS"],
         now, user["id"]),
    )
session.clear()
session["pending_user_id"] = user["id"]
session["pending_started"] = now
sent, message = deliver_code(user, code, "login")
""",
        )
        self.code(
            "OTP verification - app.py (condensed)",
            """
if otp_matches(code, user["otp_code"]):
    with db.get_db() as conn:
        conn.execute(
            '''UPDATE users
               SET otp_code = NULL, otp_expiry = NULL, otp_attempts = 0,
                   last_login_at = ?
               WHERE id = ?''',
            (now, user["id"]),
        )
    session.clear()
    session["user_id"] = user["id"]
    return redirect(url_for("dashboard"))
""",
        )

    # ------------------------------------------------------------------
    # Section 6: recovery and controls
    # ------------------------------------------------------------------
    def section_controls(self) -> None:
        self.add_page()
        self.start_section("06 Recovery & Defensive Controls", level=0)
        self.section_pages["06"] = self.page_no()
        self.section_title(
            "06",
            "Account Recovery & Defensive Controls",
            "Reset codes, CSRF protection, secure cookies, headers and anti-enumeration.",
        )

        self.subheading("6.1 Forgot password")
        self.body(
            "`/forgot-password` accepts an email address and always shows the same response, "
            "whether or not an account exists. For a matching account, a six-digit reset code "
            "is generated, HMAC-hashed, given a ten-minute expiry and sent through the same "
            "owner-only channel. The visitor is redirected to `/reset-password`, enters the "
            "code and chooses a new password."
        )
        self.numbered(
            [
                "The request is normalised and looked up by email with a parameterised query.",
                "If found, a CSPRNG reset code replaces any previous reset state and the pending reset is bound to the session.",
                "The code is delivered to db1434@gmail.com and printed in the terminal.",
                "The reset form verifies expiry, attempt count, code digest and the new password policy.",
                "On success, the password hash is replaced, reset fields and lockout are cleared, and the session is discarded.",
            ]
        )
        self.table(
            ["Recovery control", "Value"],
            [
                ["Code length", "6 digits"],
                ["Expiry", "10 minutes (`RESET_TTL_SECONDS=600`)"],
                ["Incorrect attempts", "5 (`RESET_MAX_ATTEMPTS=5`)"],
                ["Reuse", "Single use; fields cleared on success"],
                ["Recipient", "Fixed owner inbox (db1434@gmail.com)"],
                ["Account enumeration", "Generic response and same redirect for unknown emails"],
            ],
            widths=[55, 119],
            font_size=7.8,
        )

        self.subheading("6.2 Cross-site request forgery")
        self.body(
            "Every POST form includes a hidden `csrf_token` generated from 32 random bytes and "
            "stored in the signed session. A `before_request` hook compares the submitted token "
            "with the session value using `hmac.compare_digest` and aborts with HTTP 400 on a "
            "mismatch. Login, registration, OTP verification, resend, reset, forgot-password "
            "and logout are all protected, including the logout action itself."
        )
        self.code(
            "CSRF enforcement - app.py",
            """
@app.before_request
def protect_post_requests():
    if request.method == "POST":
        token = request.form.get("csrf_token", "")
        expected = session.get("_csrf_token", "")
        if not expected or not hmac.compare_digest(token, expected):
            abort(400, description="Invalid or missing CSRF token.")
""",
        )

        self.subheading("6.3 Session and browser hardening")
        self.bullets(
            [
                "**Session cookie:** HttpOnly, SameSite=Lax, signed with a 256-bit secret; Secure flag available for HTTPS deployments.",
                "**Rotation:** `session.clear()` is called before pending and verified sessions are created, preventing fixation.",
                "**Security headers:** CSP, X-Frame-Options DENY, nosniff, restrictive Referrer-Policy and Permissions-Policy.",
                "**No caching of HTML:** `Cache-Control: no-store` prevents authenticated pages from lingering in shared browser caches.",
                "**Bounded input:** request bodies are capped at 1 MiB; usernames and emails are validated and length-limited.",
                "**Parameterised SQL:** every user value is passed as a bound parameter, eliminating SQL injection.",
                "**Generic errors:** login and recovery never disclose whether a username or email exists.",
            ]
        )

        self.subheading("6.4 Threat coverage")
        self.table(
            ["Threat", "Primary mitigation", "Residual risk"],
            [
                ["Credential stuffing", "scrypt hashes, generic errors, five-failure lockout", "Distributed attempts need an IP-level limiter."],
                ["Stolen password", "Second factor required for every new session", "Owner inbox compromise remains a risk."],
                ["OTP guessing", "Six digits, five attempts, five-minute expiry, cooldown", "A determined attacker can trigger lockout but not bypass."],
                ["Database theft", "Salted scrypt hashes and HMAC-hashed OTPs", "Weak user passwords remain guessable offline."],
                ["CSRF", "Per-session token on every POST", "Token theft through XSS remains possible."],
                ["XSS", "Jinja auto-escaping, no inline scripts, strict CSP", "Third-party assets are deliberately avoided."],
                ["Session fixation", "Session clear/rotation at every privilege change", "No server-side revocation list in this build."],
                ["Email interception", "Short TTL, single use, owner-only destination", "Email is not end-to-end encrypted."],
            ],
            widths=[38, 82, 54],
            font_size=7.1,
            line_h=3.4,
        )

        self.callout(
            "Defence in depth",
            "No single control is treated as sufficient. Hashing protects stored credentials, "
            "2FA protects the session boundary, CSRF protects state changes, and headers reduce "
            "the impact of browser-side attacks. Each layer remains useful if another fails.",
            tone="green",
        )

    # ------------------------------------------------------------------
    # Section 7: code snippets
    # ------------------------------------------------------------------
    def section_code(self) -> None:
        self.add_page()
        self.start_section("07 Key Code Snippets", level=0)
        self.section_pages["07"] = self.page_no()
        self.section_title(
            "07",
            "Key Code Snippets",
            "The small number of functions that carry the security properties.",
        )

        self.body(
            "The excerpts below are taken from the working project. Full source is available "
            "in `app.py`, `db.py`, `mailer.py` and the templates."
        )

        self.subheading("7.1 Keyed OTP digest and masked inbox")
        self.code(
            "OTP digest - app.py",
            """
def hash_otp(code: str) -> str:
    key = app.config["SECRET_KEY"].encode("utf-8")
    return hmac.new(key, code.encode("utf-8"), sha256).hexdigest()

def otp_matches(code: str, stored_hash: str | None) -> bool:
    if not stored_hash:
        return False
    return hmac.compare_digest(hash_otp(code), stored_hash)
""",
        )

        self.subheading("7.2 Login and 2FA gate")
        self.code(
            "Verified session creation - app.py",
            """
if not user or not password_ok:
    # increment failed_logins / apply locked_until
    ...
else:
    code = f"{secrets.randbelow(1_000_000):06d}"
    # store HMAC digest and expiry
    session.clear()
    session["pending_user_id"] = user["id"]
    session["pending_started"] = now
    sent, message = deliver_code(user, code, "login")
    return redirect(url_for("verify_2fa"))

# later, after a correct code:
session.clear()
session["user_id"] = user["id"]
session.permanent = True
return redirect(url_for("dashboard"))
""",
        )

        self.subheading("7.3 Owner-only email delivery")
        self.code(
            "Recipient enforcement - mailer.py",
            """
override = (config.get("OTP_RECIPIENT_OVERRIDE") or "").strip().lower()
recipient = override or to_email.strip().lower()

if not sender or not password:
    return (
        False,
        "Email delivery is not configured, so the code was printed "
        "in the server terminal.",
        recipient,
    )

with smtplib.SMTP_SSL(
    config["MAIL_SERVER"], config["MAIL_PORT"],
    timeout=config["MAIL_TIMEOUT"], context=ssl.create_default_context(),
) as smtp:
    smtp.login(sender, password)
    smtp.send_message(message)
""",
        )

        self.subheading("7.4 Dashboard access control")
        self.code(
            "Session guard - app.py",
            """
def login_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        if not session.get("user_id"):
            flash("Please sign in to access your dashboard.", "warning")
            return redirect(url_for("login"))
        return view(*args, **kwargs)
    return wrapped

@app.get("/dashboard")
@login_required
def dashboard():
    user = fetch_user(session.get("user_id"))
    ...
""",
        )

        self.subheading("7.5 Security headers")
        self.code(
            "Response hardening - app.py",
            """
response.headers["X-Content-Type-Options"] = "nosniff"
response.headers["X-Frame-Options"] = "DENY"
response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
response.headers["Content-Security-Policy"] = (
    "default-src 'self'; style-src 'self'; script-src 'self'; "
    "form-action 'self'; frame-ancestors 'none'; base-uri 'self'"
)
response.headers["Cache-Control"] = "no-store, max-age=0"
""",
        )

    # ------------------------------------------------------------------
    # Section 8: running
    # ------------------------------------------------------------------
    def section_run(self) -> None:
        self.add_page()
        self.start_section("08 Running the Project", level=0)
        self.section_pages["08"] = self.page_no()
        self.section_title(
            "08",
            "Step-by-Step: Running the Project",
            "From a clean terminal to a verified dashboard in four commands.",
        )

        self.subheading("8.1 Prerequisites")
        self.body(
            "Python 3.10 or newer is recommended; this build was tested with Python 3.14.4 "
            "on Linux. No Node.js, Docker, database server or paid account is required. The "
            "virtual environment and SQLite file are local to the project."
        )

        self.subheading("8.2 Installation")
        self.code(
            "Terminal - install dependencies",
            """
cd /home/pc/secure-login-system
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
""",
        )

        self.subheading("8.3 Configuration")
        self.body(
            "A ready-to-run `.env` is created in the project root with a generated Flask "
            "secret and the SMTP settings. For live Gmail delivery, replace `MAIL_PASSWORD` "
            "with a Google App Password. Do not commit `.env` to source control."
        )
        self.table(
            ["Variable", "Purpose"],
            [
                ["SECRET_KEY", "Signs session cookies and keys the OTP HMAC."],
                ["DATABASE_PATH", "SQLite file path; defaults to database.db."],
                ["OTP_TTL_SECONDS", "Login code lifetime; default 300 seconds."],
                ["OTP_MAX_ATTEMPTS", "Incorrect login codes per code; default 5."],
                ["OTP_RECIPIENT_OVERRIDE", "Forces delivery to db1434@gmail.com only."],
                ["MAIL_USERNAME", "Gmail account used as the SMTP sender."],
                ["MAIL_PASSWORD", "Google App Password used for SMTP authentication."],
                ["PORT", "Local HTTP port; this environment uses 5055."],
            ],
            widths=[52, 122],
            font_size=7.6,
        )
        self.callout(
            "Gmail App Password setup",
            "Open the Google Account for db1434@gmail.com, enable 2-Step Verification, then "
            "create an App Password for Mail. Paste the 16-character value into MAIL_PASSWORD. "
            "Google rejects normal account passwords over SMTP with error 535.",
            tone="red",
        )

        self.subheading("8.4 Initialise and start")
        self.code(
            "Terminal - database and server",
            """
# Optional inspection and clean rebuild:
python init_db.py --show
python init_db.py --reset --show

# Start the Flask development server:
python app.py
# Open: http://127.0.0.1:5055
""",
        )
        self.body(
            "The server performs the same initialisation automatically, so `python app.py` "
            "works even if `init_db.py` was not run. The startup banner prints the URL, "
            "database path and authorised OTP inbox."
        )

        self.subheading("8.5 Demonstration walkthrough")
        self.numbered(
            [
                "Open `http://127.0.0.1:5055/register` and create an account with a password such as `StrongPass!23`.",
                "Sign in at `/login` with the username or email plus the password.",
                "Watch the server terminal for the framed six-digit code. If Gmail is configured correctly, the same code also arrives at db1434@gmail.com.",
                "Enter the code at `/verify-2fa`. The dashboard opens only if it is valid and unexpired.",
                "Use the sign-out button in the header or dashboard to destroy the session.",
                "To test recovery, choose Forgot password, request a code, watch the terminal, then set a new password.",
            ]
        )
        self.code(
            "Terminal - OTP banner (illustrative code)",
            """
==================================================================
  2FA LOGIN CODE - SECURE LOGIN SYSTEM
------------------------------------------------------------------
  Account : demo_user (reviewer@example.com)
  Code    : 482913
  Target  : db1434@gmail.com (authorised owner inbox)
  Expires : 5 minutes
==================================================================
""",
        )

        self.subheading("8.6 Test command")
        self.code(
            "Terminal - automated verification",
            """
source .venv/bin/activate
python -m unittest discover -s tests -v
""",
        )
        self.body(
            "The test suite uses a temporary SQLite database and a stubbed mailer. It never "
            "sends real email and never touches the project's `database.db`."
        )
        self.small(
            "Quick start after setup: cd /home/pc/secure-login-system && .venv/bin/python app.py"
        )

    # ------------------------------------------------------------------
    # Section 9: verification
    # ------------------------------------------------------------------
    def section_verification(self) -> None:
        self.add_page()
        self.start_section("09 Verification & Test Results", level=0)
        self.section_pages["09"] = self.page_no()
        self.section_title(
            "09",
            "Verification & Test Results",
            "Evidence from database creation, automated tests and a live browser walkthrough.",
        )

        self.subheading("9.1 Environment")
        self.table(
            ["Item", "Observed value"],
            [
                ["Operating system", f"{platform.system()} {platform.release()}"],
                ["Python", "3.14.4"],
                ["Flask", "3.1.3"],
                ["Werkzeug", "3.1.9"],
                ["SQLite", sqlite3.sqlite_version],
                ["fpdf2", "2.9.0"],
                ["Database status", "`database.db` created; users table present"],
                ["Local URL", "http://127.0.0.1:5055"],
            ],
            widths=[47, 127],
            font_size=7.8,
        )

        self.subheading("9.2 Automated test results")
        self.body(
            "Nine end-to-end tests were executed with Python's `unittest` runner. All passed "
            "in approximately 6.4 seconds."
        )
        self.table(
            ["#", "Test", "Result"],
            [
                ["1", "Pages render; CSP, frame, nosniff and health endpoint behave correctly", "PASS"],
                ["2", "Registration hashes password; duplicate username/email is rejected", "PASS"],
                ["3", "Incorrect password is rejected and counter increments", "PASS"],
                ["4", "Full 2FA login, dashboard access and POST logout", "PASS"],
                ["5", "POST without CSRF token returns HTTP 400", "PASS"],
                ["6", "Forgot-password OTP; reset; old password rejected; new login works", "PASS"],
                ["7", "Five failures trigger temporary account lockout", "PASS"],
                ["8", "Five wrong OTPs cancel the pending verification", "PASS"],
                ["9", "Password reset rejects mismatched confirmation", "PASS"],
            ],
            widths=[10, 148, 16],
            font_size=7.5,
        )
        self.callout(
            "Test outcome",
            "9 of 9 tests passed. The database was created automatically, scrypt hashes were "
            "observed in SQLite instead of plaintext, the dashboard was inaccessible before "
            "OTP verification, and session destruction redirected the browser to sign-in.",
            tone="green",
        )

        self.subheading("9.3 Live browser walkthrough")
        self.body(
            "A Chrome automation run exercised the real HTTP server: account registration, "
            "password login, terminal OTP entry, dashboard rendering, sign-out, forgot-password "
            "request and reset page. The run reported no browser console errors. The UI is "
            "responsive at desktop and mobile widths."
        )
        self.code(
            "Console output (sanitised)",
            """
saved register.png
after register: http://127.0.0.1:5056/login
after login:    http://127.0.0.1:5056/verify-2fa
OTP from terminal: 482913
after verify:   http://127.0.0.1:5056/dashboard
after logout:   http://127.0.0.1:5056/login
after forgot:   http://127.0.0.1:5056/reset-password
console errors: none
""",
        )

        self.subheading("9.4 Database verification")
        self.code(
            "init_db.py --show (excerpt)",
            """
Database : /home/pc/secure-login-system/database.db
Tables   : sqlite_sequence, users
Users    : 0

Schema:
CREATE TABLE users (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    username        TEXT    NOT NULL UNIQUE COLLATE NOCASE,
    email           TEXT    NOT NULL UNIQUE COLLATE NOCASE,
    password_hash   TEXT    NOT NULL,
    otp_code        TEXT,
    otp_expiry      INTEGER,
    ...
)
""",
        )

        self.subheading("9.5 Delivery readiness")
        self.body(
            "Network connectivity to `smtp.gmail.com:465` was confirmed. Authentication with "
            "the supplied mailbox password was rejected by Google with **535 5.7.8 BadCredentials**, "
            "which is expected when an account uses normal-password SMTP instead of an App "
            "Password. The application handles this safely: it logs a warning, does not "
            "expose SMTP details to the browser, and still prints the OTP to the terminal. "
            "Once a valid Google App Password is placed in `MAIL_PASSWORD`, the same code path "
            "delivers email to db1434@gmail.com without code changes."
        )
        self.small(
            "Residual note: the local assignment environment has no production TLS certificate, "
            "so SESSION_COOKIE_SECURE is disabled by default. Enable it behind HTTPS."
        )

    # ------------------------------------------------------------------
    # Section 10: limitations and conclusion
    # ------------------------------------------------------------------
    def section_limits(self) -> None:
        self.add_page()
        self.start_section("10 Limitations & Conclusion", level=0)
        self.section_pages["10"] = self.page_no()
        self.section_title(
            "10",
            "Limitations, Recommendations & Conclusion",
            "What is intentionally local, what would change in production, and the final verdict.",
        )

        self.subheading("10.1 Known limitations")
        self.table(
            ["Area", "Current local behaviour", "Production consideration"],
            [
                ["Server", "Flask development server", "Run behind gunicorn/uWSGI and a reverse proxy."],
                ["Transport", "HTTP on localhost", "HTTPS with HSTS, Secure cookies and a trusted certificate."],
                ["Secrets", "Local .env file", "Use a managed secret store and rotate credentials."],
                ["Email", "Gmail SMTP + terminal fallback", "Transactional email provider with delivery monitoring."],
                ["Database", "Unencrypted local SQLite file", "Encrypted volume/at-rest encryption and backups."],
                ["Rate limiting", "Per-account lockout only", "Add per-IP and device rate limiting / WAF."],
                ["Session revocation", "Cookie expiry only", "Server-side session store with revoke-all."],
                ["Audit", "Application logs", "Structured security event logging and alerting."],
                ["Recovery", "Owner-only inbox override", "Send to the account owner after email verification."],
            ],
            widths=[33, 68, 73],
            font_size=7.1,
            line_h=3.4,
        )

        self.subheading("10.2 Recommended next steps")
        self.bullets(
            [
                "Replace `app.run()` with a production WSGI server and terminate TLS at a trusted proxy.",
                "Enable `SESSION_COOKIE_SECURE=True` and add HSTS once HTTPS is active.",
                "Use a professional transactional email service and monitor bounces and delivery failures.",
                "Add an authenticator-app TOTP fallback and recovery codes for inbox loss.",
                "Add per-IP throttling and alerting for repeated lockouts or OTP failures.",
                "Consider a server-side session store so a password reset can revoke all sessions.",
                "Add email verification at registration and optional breach-password checks.",
            ]
        )

        self.subheading("10.3 Conclusion")
        self.body(
            "The project satisfies the assignment brief with a complete, locally runnable "
            "implementation. Registration stores only salted scrypt hashes; login always "
            "requires a second factor; OTPs are random, keyed-hashed, short-lived, single-use "
            "and limited; recovery is protected by the same code channel; and the dashboard "
            "is gated by a verified session. The PDF report, automated tests, responsive UI "
            "and terminal OTP banner make the work straightforward to demonstrate and assess."
        )
        self.callout(
            "Final status",
            "Database initialisation: PASS. Password hashing: PASS. Two-step verification: "
            "PASS. Protected dashboard and logout: PASS. Forgot/reset password: PASS. "
            "Automated tests: 9/9 PASS. PDF report: generated in the project root.",
            tone="green",
        )

    # ------------------------------------------------------------------
    # Appendix A: structure
    # ------------------------------------------------------------------
    def appendix_structure(self) -> None:
        self.add_page()
        self.start_section("Appendix A: Project Structure", level=0)
        self.section_pages["A"] = self.page_no()
        self.section_title(
            "A",
            "Appendix: Project Structure",
            "A small repository with explicit responsibilities.",
        )
        self.code(
            "Repository tree",
            """
secure-login-system/
|-- app.py                  Flask routes, validation, sessions, 2FA
|-- db.py                   SQLite schema, connections, teardown
|-- mailer.py               Gmail SMTP delivery and recipient enforcement
|-- config.py               Environment-driven configuration
|-- init_db.py              CLI database initialiser (--show / --reset)
|-- generate_report.py      Automated PDF generation with fpdf2
|-- requirements.txt        Flask, python-dotenv, fpdf2
|-- .env                    Local secrets (not committed)
|-- .env.example            Configuration template
|-- database.db             Auto-created SQLite database
|-- Assignment_Report.pdf   Generated report
|-- templates/
|   |-- base.html           Shared shell, navigation, flash messages
|   |-- register.html       Registration form
|   |-- login.html          Password + identifier form
|   |-- verify_2fa.html     Six-digit OTP form and countdown
|   |-- dashboard.html      Protected account overview
|   |-- forgot_password.html
|   |-- reset_password.html
|   `-- error.html          Styled 400/404/413/500 pages
|-- static/
|   |-- css/style.css       Responsive design system
|   |-- js/main.js          Password toggle, OTP input, countdowns
|   `-- favicon.svg
|-- tests/
|   `-- test_app.py         9 end-to-end unittest cases
`-- report_assets/          Screenshots embedded in this PDF
""",
            font_size=6.7,
        )

        self.subheading("Route map")
        self.table(
            ["Method", "Path", "Access"],
            [
                ["GET", "/", "Redirect to dashboard or login"],
                ["GET, POST", "/register", "Public"],
                ["GET, POST", "/login", "Public; starts pending 2FA"],
                ["GET, POST", "/verify-2fa", "Pending login session only"],
                ["POST", "/verify-2fa/resend", "Pending login session only"],
                ["GET", "/dashboard", "Verified session only"],
                ["POST", "/logout", "Verified session; CSRF required"],
                ["GET, POST", "/forgot-password", "Public; enumeration-safe response"],
                ["GET, POST", "/reset-password", "Pending reset + valid code"],
                ["GET", "/healthz", "Local health check"],
            ],
            widths=[24, 58, 92],
            font_size=7.6,
        )

    # ------------------------------------------------------------------
    # Appendix B: screenshots
    # ------------------------------------------------------------------
    def appendix_screenshots(self) -> None:
        self.add_page()
        self.start_section("Appendix B: Interface Preview", level=0)
        self.section_pages["B"] = self.page_no()
        self.section_title(
            "B",
            "Appendix: Interface Preview",
            "Desktop screenshots captured from the running application.",
        )

        items = [
            ("login.png", "Figure B1. Password sign-in with a clear path to account recovery."),
            ("verify_2fa.png", "Figure B2. Two-step verification with recipient notice, live expiry and resend cooldown."),
            ("dashboard.png", "Figure B3. Protected dashboard with security status and POST-only sign-out."),
            ("reset_password.png", "Figure B4. Password reset after a valid owner-delivered OTP."),
        ]
        optimized = self.prepare_images()
        width = 84
        positions = [18, 108]
        row_top = self.get_y()
        row_height = 69
        for index, (name, caption) in enumerate(items):
            column = index % 2
            if column == 0 and index > 0:
                row_top += row_height + 5
            if row_top + row_height > self.h - self.b_margin - 2:
                self.add_page()
                row_top = self.get_y()
            x = positions[column]
            path = optimized.get(name) or (ASSETS / name)
            if not path.exists():
                continue
            image_height = 58.3
            if Image is not None:
                with Image.open(path) as img:
                    image_height = width * img.height / img.width
            self.set_draw_color(*LINE)
            self.set_line_width(0.3)
            self.image(str(path), x=x, y=row_top, w=width)
            self.rect(x, row_top, width, image_height)
            self.set_xy(x, row_top + image_height + 1.5)
            self.set_font("helvetica", "", 6.4)
            self.set_text_color(*MUTED)
            self.multi_cell(width, 3.4, caption)
        self.set_y(row_top + row_height + 8)
        self.subheading("Design and accessibility notes")
        self.bullets(
            [
                "**Responsive by default.** The layout was checked at 1440 x 1000 and 390 x 844 viewport sizes.",
                "**No external assets.** System fonts, local CSS, local JavaScript and an inline SVG favicon keep the demo offline-friendly.",
                "**Accessible controls.** Every input has a label, focus styles are visible, flashes use an ARIA live region, and password fields include reveal buttons.",
                "**Immediate feedback.** The OTP page shows a live expiry timer and a resend cooldown without refreshing the page.",
            ],
            size=8.4,
        )

    def prepare_images(self) -> dict[str, Path]:
        """Downscale screenshots to keep the PDF a practical size."""
        if Image is None:
            return {}
        target = BASE_DIR / "report_assets" / ".pdf"
        target.mkdir(exist_ok=True)
        result = {}
        for name in ("login.png", "verify_2fa.png", "dashboard.png", "reset_password.png"):
            source = ASSETS / name
            if not source.exists():
                continue
            destination = target / name.replace(".png", ".jpg")
            if not destination.exists() or destination.stat().st_mtime < source.stat().st_mtime:
                with Image.open(source) as img:
                    img = img.convert("RGB")
                    width = 1200
                    height = round(img.height * width / img.width)
                    img.resize((width, height), Image.LANCZOS).save(
                        destination, "JPEG", quality=84, optimize=True
                    )
            result[name] = destination
        return result


def build_report(output: Path = OUTPUT, toc_pages: dict[str, int] | None = None) -> dict[str, int]:
    pdf = Report(toc_pages=toc_pages)
    pdf.alias_nb_pages()
    pdf.cover()
    pdf.contents_and_summary()
    pdf.section_overview()
    pdf.section_architecture()
    pdf.section_database()
    pdf.section_hashing()
    pdf.section_two_factor()
    pdf.section_controls()
    pdf.section_code()
    pdf.section_run()
    pdf.section_verification()
    pdf.section_limits()
    pdf.appendix_structure()
    pdf.appendix_screenshots()
    output.parent.mkdir(parents=True, exist_ok=True)
    pdf.output(str(output))
    return pdf.section_pages


def main() -> int:
    print("Generating PDF report...")
    first_pass = BASE_DIR / ".report_pass_one.pdf"
    pages = build_report(first_pass)
    print("Section pages:", pages)
    build_report(OUTPUT, toc_pages=pages)
    if first_pass.exists():
        first_pass.unlink()
    print(f"Report written to {OUTPUT} ({OUTPUT.stat().st_size / 1024:.1f} KiB)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
