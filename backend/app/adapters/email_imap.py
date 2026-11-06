import email
import imaplib
import re
from dataclasses import dataclass
from email.header import decode_header, make_header
from email.utils import parsedate_to_datetime

from app.core.settings import get_settings


@dataclass
class InboundMail:
    imap_message_id: str
    from_email: str
    to_email: str
    subject: str
    body_text: str
    in_reply_to: str | None
    references: list[str]
    sent_at: str | None
    uid: str


def _decode(value: str | None) -> str:
    if not value:
        return ""
    try:
        return str(make_header(decode_header(value)))
    except Exception:  # noqa: BLE001
        return value


def _extract_email(raw: str) -> str:
    m = re.search(r"<([^>]+)>", raw)
    return (m.group(1) if m else raw).strip().lower()


def _body_text(msg: email.message.Message) -> str:
    if msg.is_multipart():
        parts: list[str] = []
        for part in msg.walk():
            ctype = part.get_content_type()
            if ctype == "text/plain" and "attachment" not in str(part.get("Content-Disposition", "")):
                payload = part.get_payload(decode=True) or b""
                charset = part.get_content_charset() or "utf-8"
                parts.append(payload.decode(charset, errors="replace"))
        if parts:
            return "\n".join(parts).strip()
    payload = msg.get_payload(decode=True) or b""
    charset = msg.get_content_charset() or "utf-8"
    text = payload.decode(charset, errors="replace")
    # crude HTML strip
    return re.sub(r"<[^>]+>", " ", text).strip()


def fetch_unseen() -> list[InboundMail]:
    settings = get_settings()
    if not settings.imap_host or not settings.imap_user:
        return []

    mail = imaplib.IMAP4_SSL(settings.imap_host, settings.imap_port)
    try:
        mail.login(settings.imap_user, settings.imap_password)
        mail.select("INBOX")
        status, data = mail.search(None, "UNSEEN")
        if status != "OK" or not data or not data[0]:
            return []
        results: list[InboundMail] = []
        for uid in data[0].split():
            status, msg_data = mail.fetch(uid, "(RFC822)")
            if status != "OK" or not msg_data or not msg_data[0]:
                continue
            raw = msg_data[0][1]
            msg = email.message_from_bytes(raw)
            message_id = (msg.get("Message-ID") or f"uid-{uid.decode()}").strip()
            refs_raw = msg.get("References") or ""
            references = [r.strip() for r in refs_raw.split() if r.strip()]
            sent_at = None
            if msg.get("Date"):
                try:
                    sent_at = parsedate_to_datetime(msg.get("Date")).isoformat()
                except Exception:  # noqa: BLE001
                    sent_at = None
            results.append(
                InboundMail(
                    imap_message_id=message_id,
                    from_email=_extract_email(_decode(msg.get("From"))),
                    to_email=_extract_email(_decode(msg.get("To"))),
                    subject=_decode(msg.get("Subject")),
                    body_text=_body_text(msg),
                    in_reply_to=(msg.get("In-Reply-To") or "").strip() or None,
                    references=references,
                    sent_at=sent_at,
                    uid=uid.decode(),
                )
            )
            mail.store(uid, "+FLAGS", "\\Seen")
        return results
    finally:
        try:
            mail.logout()
        except Exception:  # noqa: BLE001
            pass
