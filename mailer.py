"""SMTP delivery for one-time passcodes.

The assignment deliberately avoids third-party email APIs. Gmail SMTP works with
an App Password; if delivery is unavailable, the caller still prints the code to
the terminal so the flow can be demonstrated offline.
"""

from __future__ import annotations

import smtplib
import ssl
from email.message import EmailMessage
from email.utils import formataddr

from flask import current_app


def _build_message(
    *,
    sender: str,
    recipient: str,
    code: str,
    purpose: str,
    username: str,
    account_email: str,
    ttl_minutes: int,
) -> EmailMessage:
    labels = {
        "login": ("Your sign-in verification code", "sign in"),
        "password_reset": ("Your password reset code", "reset your password"),
    }
    subject_label, action_label = labels.get(purpose, labels["login"])
    subject = f"{subject_label} - Secure Login System"

    text_body = f"""Hello {username},

Use the following one-time passcode to {action_label}:

    {code}

This code expires in {ttl_minutes} minutes and can be used once.
Account: {username} ({account_email})

If you did not request this code, you can safely ignore this email.
Never share this code with anyone.

Secure Login System
"""
    html_body = f"""\
<!doctype html>
<html lang="en">
  <body style="margin:0;padding:0;background:#eef2ff;font-family:Arial,Helvetica,sans-serif;color:#0f172a;">
    <table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="background:#eef2ff;padding:32px 12px;">
      <tr>
        <td align="center">
          <table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="max-width:560px;background:#ffffff;border-radius:16px;overflow:hidden;border:1px solid #dbe4ff;">
            <tr>
              <td style="background:#111c44;padding:28px 32px;color:#ffffff;">
                <div style="font-size:12px;letter-spacing:2px;color:#93c5fd;text-transform:uppercase;">Secure Login System</div>
                <div style="font-size:24px;font-weight:700;margin-top:6px;">{subject_label}</div>
              </td>
            </tr>
            <tr>
              <td style="padding:32px;">
                <p style="margin:0 0 16px;font-size:16px;">Hello <strong>{username}</strong>,</p>
                <p style="margin:0 0 24px;font-size:15px;line-height:1.6;color:#334155;">
                  Use the one-time passcode below to {action_label}. It expires in
                  <strong>{ttl_minutes} minutes</strong> and can be used only once.
                </p>
                <div style="background:#f1f5ff;border:1px dashed #93a8ff;border-radius:12px;padding:22px;text-align:center;">
                  <div style="font-size:12px;letter-spacing:2px;color:#64748b;text-transform:uppercase;margin-bottom:8px;">Verification code</div>
                  <div style="font-size:38px;font-weight:700;letter-spacing:10px;color:#1d4ed8;">{code}</div>
                </div>
                <p style="margin:24px 0 0;font-size:13px;line-height:1.6;color:#475569;">
                  Requested for account: <strong>{username}</strong> ({account_email})<br>
                  If you did not request this code, ignore this email. Never share it with anyone.
                </p>
              </td>
            </tr>
            <tr>
              <td style="background:#f8fafc;padding:16px 32px;border-top:1px solid #e2e8f0;font-size:12px;color:#64748b;">
                Automated message from Secure Login System. Replies are not monitored.
              </td>
            </tr>
          </table>
        </td>
      </tr>
    </table>
  </body>
</html>
"""
    message = EmailMessage()
    message["Subject"] = subject
    message["From"] = formataddr((current_app.config["MAIL_FROM_NAME"], sender))
    message["To"] = recipient
    message["X-Auto-Response-Suppress"] = "All"
    message.set_content(text_body)
    message.add_alternative(html_body, subtype="html")
    return message


def send_otp_email(
    *,
    to_email: str,
    code: str,
    purpose: str,
    username: str,
    account_email: str,
    ttl_minutes: int,
) -> tuple[bool, str, str]:
    """Send an OTP to the enforced owner inbox.

    Returns ``(sent, message, final_recipient)``. The recipient is always
    ``OTP_RECIPIENT_OVERRIDE`` when configured, so codes can never be delivered
    to an arbitrary address supplied by a visitor.
    """
    config = current_app.config
    sender = (config.get("MAIL_USERNAME") or "").strip()
    password = config.get("MAIL_PASSWORD") or ""
    override = (config.get("OTP_RECIPIENT_OVERRIDE") or "").strip().lower()
    recipient = override or to_email.strip().lower()

    if not sender or not password:
        return (
            False,
            "Email delivery is not configured, so the code was printed in the server terminal.",
            recipient,
        )

    message = _build_message(
        sender=sender,
        recipient=recipient,
        code=code,
        purpose=purpose,
        username=username,
        account_email=account_email,
        ttl_minutes=ttl_minutes,
    )

    try:
        context = ssl.create_default_context()
        if config.get("MAIL_USE_SSL", True):
            with smtplib.SMTP_SSL(
                config["MAIL_SERVER"],
                config["MAIL_PORT"],
                timeout=config["MAIL_TIMEOUT"],
                context=context,
            ) as smtp:
                smtp.login(sender, password)
                smtp.send_message(message)
        else:
            with smtplib.SMTP(
                config["MAIL_SERVER"],
                config["MAIL_PORT"],
                timeout=config["MAIL_TIMEOUT"],
            ) as smtp:
                smtp.ehlo()
                smtp.starttls(context=context)
                smtp.ehlo()
                smtp.login(sender, password)
                smtp.send_message(message)
    except (smtplib.SMTPException, OSError, TimeoutError) as exc:
        current_app.logger.warning(
            "OTP email delivery failed (%s): %s", type(exc).__name__, exc
        )
        return (
            False,
            "Email delivery failed, so the code was printed in the server terminal.",
            recipient,
        )

    current_app.logger.info("OTP email accepted by SMTP for %s", recipient)
    return True, f"Verification code sent to {recipient}.", recipient
