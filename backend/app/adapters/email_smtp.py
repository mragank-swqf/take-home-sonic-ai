import smtplib
from email.message import EmailMessage

from app.core.settings import get_settings


def send_email(*, to_email: str, subject: str, body: str, message_id: str | None = None) -> str:
    settings = get_settings()
    if not settings.smtp_host or not settings.smtp_user:
        raise RuntimeError("SMTP is not configured")

    msg = EmailMessage()
    from_addr = settings.org_mailbox_address or settings.smtp_user
    msg["From"] = from_addr
    msg["To"] = to_email
    msg["Subject"] = subject
    if message_id:
        msg["Message-ID"] = message_id
    msg.set_content(body)

    with smtplib.SMTP(settings.smtp_host, settings.smtp_port, timeout=30) as smtp:
        smtp.starttls()
        if settings.smtp_password:
            smtp.login(settings.smtp_user, settings.smtp_password)
        smtp.send_message(msg)

    return msg["Message-ID"] or message_id or ""
