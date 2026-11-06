from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone
from typing import Any

from fastapi import HTTPException
from pymongo.database import Database

from app.adapters import email_smtp
from app.core.settings import get_settings
from app.repositories import customers as customers_repo
from app.repositories import invoices as invoices_repo
from app.repositories import organization as org_repo
from app.services.draft_validator import reminder_body


def _cooldown_active(customer: dict[str, Any], now: datetime) -> bool:
    raw = customer.get("last_reminder_sent_at")
    if not raw:
        return False
    if isinstance(raw, str):
        raw = datetime.fromisoformat(raw.replace("Z", "+00:00"))
    if raw.tzinfo is None:
        raw = raw.replace(tzinfo=timezone.utc)
    minutes = get_settings().reminder_cooldown_minutes
    return raw + timedelta(minutes=minutes) > now


def _get_or_create_conversation(db: Database, customer_id: str, subject: str) -> Any:
    existing = db["conversations"].find_one(
        {"customer_id": customer_id, "status": {"$in": ["open", "needs_attention"]}}
    )
    if existing:
        return existing["_id"]
    return db["conversations"].insert_one(
        {
            "customer_id": customer_id,
            "subject": subject,
            "status": "open",
            "needs_attention_reason": None,
            "pending_draft": None,
            "pending_intent": None,
            "last_message_at": datetime.now(timezone.utc),
            "created_at": datetime.now(timezone.utc),
        }
    ).inserted_id


def send_reminders(
    db: Database,
    *,
    customer_ids: list[str] | None = None,
    force: bool = False,
) -> dict[str, Any]:
    settings = get_settings()
    as_of = settings.as_of_date()
    org = org_repo.get_organization(db)
    if not org:
        raise HTTPException(status_code=500, detail="Organization missing")

    customers = customers_repo.list_customers(db)
    if customer_ids:
        wanted = set(customer_ids)
        customers = [c for c in customers if c["customer_id"] in wanted]

    sent: list[dict[str, Any]] = []
    skipped: list[dict[str, str]] = []
    now = datetime.now(timezone.utc)

    if not settings.smtp_host or not settings.smtp_user:
        for c in customers:
            skipped.append({"customer_id": c["customer_id"], "reason": "smtp_not_configured"})
        return {"sent": sent, "skipped": skipped}

    for customer in customers:
        cid = customer["customer_id"]
        overdue = invoices_repo.list_invoices(
            db, as_of=as_of, customer_id=cid, overdue_only=True
        )
        overdue = [i for i in overdue if i["status"] == "sent" and i["balance_due_minor"] > 0]
        if not overdue:
            skipped.append({"customer_id": cid, "reason": "no_overdue"})
            continue
        if not customer.get("contact_email"):
            skipped.append({"customer_id": cid, "reason": "no_contact_email"})
            continue
        if not force and _cooldown_active(customer, now):
            skipped.append({"customer_id": cid, "reason": "cooldown_active"})
            continue

        subject = f"Overdue invoices — {org['name']}"
        body = reminder_body(contact_name=customer["contact_name"], invoices=overdue, org=org)
        message_id = f"<reminder-{cid}-{uuid.uuid4().hex}@acmecorp.local>"
        try:
            email_smtp.send_email(
                to_email=customer["contact_email"],
                subject=subject,
                body=body,
                message_id=message_id,
            )
        except Exception as exc:  # noqa: BLE001
            raise HTTPException(status_code=502, detail="SMTP send failed") from exc

        conv_id = _get_or_create_conversation(db, cid, subject)
        db["messages"].insert_one(
            {
                "conversation_id": conv_id,
                "direction": "outbound",
                "from_email": settings.org_mailbox_address or settings.smtp_user,
                "to_email": customer["contact_email"],
                "subject": subject,
                "body_text": body,
                "imap_message_id": message_id,
                "in_reply_to": None,
                "references": [],
                "sent_at": now,
                "kind": "reminder",
                "llm_intent": None,
                "llm_confidence": None,
                "validation_passed": True,
            }
        )
        db["conversations"].update_one(
            {"_id": conv_id},
            {"$set": {"last_message_at": now, "status": "open"}},
        )
        customers_repo.set_reminder_sent(db, cid, now)
        sent.append(
            {
                "customer_id": cid,
                "invoice_numbers": [i["invoice_number"] for i in overdue],
                "message_id": message_id,
                "conversation_id": str(conv_id),
            }
        )

    return {"sent": sent, "skipped": skipped}
