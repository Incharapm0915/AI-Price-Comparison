"""Email notification, as a swappable abstraction (per the brief).

If SMTP is configured (`SMTP_HOST` set), sends a real email. Otherwise —
the default, so the whole app works with zero external accounts — logs the
message instead of sending it, clearly labeled so it's never mistaken for
an actual delivery.
"""
from __future__ import annotations

import smtplib
from email.message import EmailMessage

from app.config import get_settings
from app.utils.logging import get_logger

logger = get_logger(__name__)


def send_email(to: str, subject: str, body: str) -> bool:
    """Returns True if the email was actually sent (or would have been, in
    log-only mode), False if a real send was attempted and failed."""
    settings = get_settings()

    if not settings.smtp_host:
        logger.info("[email:not-configured] to=%s subject=%r\n%s", to, subject, body)
        return True

    message = EmailMessage()
    message["From"] = settings.alert_from_email
    message["To"] = to
    message["Subject"] = subject
    message.set_content(body)

    try:
        with smtplib.SMTP(settings.smtp_host, settings.smtp_port, timeout=10) as server:
            server.starttls()
            if settings.smtp_user:
                server.login(settings.smtp_user, settings.smtp_password)
            server.send_message(message)
        return True
    except (smtplib.SMTPException, OSError):
        logger.exception("Failed to send email to %s", to)
        return False
