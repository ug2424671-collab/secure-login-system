"""
test_email.py - diagnose Gmail SMTP configuration for the OTP emails.

Usage:
    python test_email.py [recipient@example.com]

It checks that GMAIL_ADDRESS and GMAIL_APP_PASSWORD are set, then attempts to
send a test message through Gmail. Helpful error messages are printed instead of
silently falling back to the terminal/banner.
"""

import os
import smtplib
import sys
from email.message import EmailMessage

from env_utils import load_env_file

load_env_file()

sender = os.environ.get("GMAIL_ADDRESS", "").strip()
password = os.environ.get("GMAIL_APP_PASSWORD", "").strip()
recipient = (sys.argv[1] if len(sys.argv) > 1 else sender).strip()

print("GMAIL_ADDRESS      : {}".format(sender or "<not set>"))
print("GMAIL_APP_PASSWORD : {}".format("set ({} chars)".format(len(password)) if password else "<not set>"))
print("Recipient          : {}".format(recipient or "<not set>"))
print("-" * 60)

if not sender or not password:
    print("SMTP is NOT configured. The app will keep using the terminal/banner.")
    print()
    print("To enable email delivery:")
    print("  1. Google Account -> Security -> 2-Step Verification -> App passwords")
    print("  2. Generate an app password for Mail (16 characters, no spaces).")
    print("  3. Run:")
    print("       export GMAIL_ADDRESS={}".format(sender or "you@gmail.com"))
    print("       export GMAIL_APP_PASSWORD='your-16-char-app-password'")
    print("       python test_email.py")
    sys.exit(1)

if len(password.replace(" ", "")) != 16:
    print("WARNING: a Gmail App Password is normally 16 characters (spaces ignored).")
    print("A normal Google account password will NOT work here.")
    print()

if not recipient:
    print("No recipient address provided.")
    sys.exit(1)

message = EmailMessage()
message["Subject"] = "SecureAuth SMTP test"
message["From"] = sender
message["To"] = recipient
message.set_content(
    "This is a test message from the SecureAuth project.\n"
    "If you received it, OTP email delivery is configured correctly.\n"
)

try:
    with smtplib.SMTP_SSL("smtp.gmail.com", 465, timeout=15) as smtp:
        smtp.login(sender, password)
        smtp.send_message(message)
    print("SUCCESS: test email sent to {}.".format(recipient))
except Exception as exc:
    print("FAILED: {}".format(exc))
    print()
    print("Common causes:")
    print("  - Using the normal Google password instead of a 16-char App Password.")
    print("  - App passwords require 2-Step Verification to be enabled on the account.")
    print("  - A typo in GMAIL_ADDRESS, or the account is not a Gmail account.")
    print("  - Network/firewall blocking smtp.gmail.com port 465.")
    sys.exit(1)
