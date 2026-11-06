import json
from datetime import datetime, timezone
from pathlib import Path

from pymongo.database import Database

from app.core.settings import get_settings
from app.services.money import to_minor

SEED_VERSION = "data-v1"

APP_COLLECTIONS = (
    "organization",
    "customers",
    "invoices",
    "conversations",
    "messages",
    "payments",
    "payment_claims",
    "bank_statement_uploads",
    "bank_statement_rows",
    "meta",
)


def _data_path(name: str) -> Path:
    return Path(get_settings().data_dir) / name


def _load_json(name: str):
    with _data_path(name).open(encoding="utf-8") as f:
        return json.load(f)


def db_is_empty(db: Database) -> bool:
    if db["meta"].find_one({"_id": "seed"}):
        return False
    return db["customers"].estimated_document_count() == 0


def seed_if_empty(db: Database) -> bool:
    if not db_is_empty(db):
        return False
    reset_and_seed(db)
    return True


def reset_and_seed(db: Database) -> dict[str, int]:
    for name in APP_COLLECTIONS:
        db[name].delete_many({})

    org = _load_json("organization.json")
    org["_id"] = "acme"
    db["organization"].insert_one(org)

    customers = _load_json("customers.json")
    for c in customers:
        c["contact_email_lower"] = c["contact_email"].strip().lower()
        c["last_reminder_sent_at"] = None
    if customers:
        db["customers"].insert_many(customers)

    invoices_raw = _load_json("invoices.json")
    invoices = []
    for inv in invoices_raw:
        line_items = [
            {
                "description": item["description"],
                "quantity": item["quantity"],
                "unit_price_minor": to_minor(item["unit_price"]),
                "amount_minor": to_minor(item["amount"]),
            }
            for item in inv["line_items"]
        ]
        invoices.append(
            {
                "invoice_number": inv["invoice_number"],
                "customer_id": inv["customer_id"],
                "customer_name": inv["customer_name"],
                "po_number": inv.get("po_number"),
                "invoice_date": inv["invoice_date"],
                "due_date": inv["due_date"],
                "payment_terms": inv["payment_terms"],
                "currency": inv["currency"],
                "line_items": line_items,
                "subtotal_minor": to_minor(inv["subtotal"]),
                "discount_minor": to_minor(inv["discount"]),
                "tax_name": inv["tax_name"],
                "tax_minor": to_minor(inv["tax"]),
                "total_minor": to_minor(inv["total"]),
                "amount_paid_minor": to_minor(inv["amount_paid"]),
                "balance_due_minor": to_minor(inv["balance_due"]),
                "status": inv["status"],
            }
        )
    if invoices:
        db["invoices"].insert_many(invoices)

    db["customers"].create_index("customer_id", unique=True)
    db["customers"].create_index("contact_email_lower", unique=True)
    db["invoices"].create_index("invoice_number", unique=True)
    db["invoices"].create_index([("customer_id", 1), ("status", 1)])
    db["messages"].create_index("imap_message_id", unique=True, sparse=True)
    db["bank_statement_uploads"].create_index("content_sha256", unique=True)

    db["meta"].insert_one(
        {
            "_id": "seed",
            "seeded_at": datetime.now(timezone.utc),
            "seed_version": SEED_VERSION,
        }
    )

    return {"customers": len(customers), "invoices": len(invoices)}
