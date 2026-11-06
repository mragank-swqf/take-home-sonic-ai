from typing import Any

from pymongo import ReturnDocument
from pymongo.database import Database


def _serialize(doc: dict[str, Any]) -> dict[str, Any]:
    out = dict(doc)
    out.pop("_id", None)
    if out.get("last_reminder_sent_at"):
        out["last_reminder_sent_at"] = out["last_reminder_sent_at"].isoformat()
    return out


def list_customers(db: Database) -> list[dict[str, Any]]:
    return [_serialize(d) for d in db["customers"].find().sort("customer_id", 1)]


def get_customer(db: Database, customer_id: str) -> dict[str, Any] | None:
    doc = db["customers"].find_one({"customer_id": customer_id})
    return _serialize(doc) if doc else None


def get_customer_by_email(db: Database, email: str) -> dict[str, Any] | None:
    doc = db["customers"].find_one({"contact_email_lower": email.strip().lower()})
    return _serialize(doc) if doc else None


def update_contact_email(db: Database, customer_id: str, email: str) -> dict[str, Any] | None:
    lower = email.strip().lower()
    clash = db["customers"].find_one(
        {"contact_email_lower": lower, "customer_id": {"$ne": customer_id}}
    )
    if clash:
        raise ValueError("email_taken")
    result = db["customers"].find_one_and_update(
        {"customer_id": customer_id},
        {"$set": {"contact_email": email.strip(), "contact_email_lower": lower}},
        return_document=ReturnDocument.AFTER,
    )
    return _serialize(result) if result else None


def clear_reminder_cooldowns(db: Database) -> None:
    db["customers"].update_many({}, {"$set": {"last_reminder_sent_at": None}})


def set_reminder_sent(db: Database, customer_id: str, when) -> None:
    db["customers"].update_one(
        {"customer_id": customer_id},
        {"$set": {"last_reminder_sent_at": when}},
    )
