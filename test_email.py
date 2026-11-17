"""
test_email.py - diagnose and test the SMTP configuration.

Usage:
    python test_email.py [recipient@example.com]

Reads credentials from .env (or the environment), prints the active
configuration (never the password), then sends a test message.
"""

import sys

import mailer

recipient = (sys.argv[1] if len(sys.argv) > 1 else mailer.SMTP_USER).strip()
config = mailer.config_summary()

print("SMTP host   : {}".format(config["host"]))
print("SMTP port   : {} ({})".format(config["port"], config["secure"]))
print("SMTP user   : {}".format(config["user"] or "<not set>"))
print("SMTP sender : {}".format(config["sender"] or "<not set>"))
print("SMTP pass   : {}".format(config["password"]))
print("Recipient   : {}".format(recipient or "<not set>"))
print("-" * 60)

if not mailer.is_configured():
    print("SMTP is NOT configured. Codes cannot be delivered by email.")
    print()
    print("Options:")
    print("  A) Gmail: create an App Password at https://myaccount.google.com/apppasswords")
    print("     then set in .env:")
    print("       SMTP_HOST=smtp.gmail.com")
    print("       SMTP_PORT=465")
    print("       SMTP_SECURE=ssl")
    print("       SMTP_USER=you@gmail.com")
    print("       SMTP_PASS=your-16-char-app-password")
    print("       SMTP_FROM=you@gmail.com")
    print("  B) Any SMTP provider: set SMTP_HOST / SMTP_PORT / SMTP_SECURE /")
    print("     SMTP_USER / SMTP_PASS / SMTP_FROM in .env.")
    sys.exit(1)

if not recipient:
    print("No recipient address provided.")
    sys.exit(1)

ok, detail = mailer.send_email(
    recipient,
    "SecureAuth SMTP test",
    "This is a test message from the SecureAuth project.\n"
    "If you received it, OTP email delivery is configured correctly.\n",
)

if ok:
    print("SUCCESS: test email sent to {}.".format(recipient))
else:
    print("FAILED: {}".format(detail))
    print()
    print("Common causes:")
    print("  - Gmail used a normal password instead of a 16-char App Password.")
    print("  - Wrong SMTP host/port, or the provider blocks this network.")
    print("  - STARTTLS expected on 587 but SMTP_SECURE is not set to starttls.")
    sys.exit(1)
