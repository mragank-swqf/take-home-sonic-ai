from datetime import date
from typing import Any

from pymongo.database import Database

from app.services.dates import is_overdue


def _serialize(doc: dict[str, Any], as_of: date) -> dict[str, Any]:
    out = dict(doc)
    out.pop("_id", None)
    balance = int(out.get("balance_due_minor", 0))
    out["unpaid_amount_minor"] = balance
    out["is_overdue"] = is_overdue(
        status=out.get("status", ""),
        balance_due_minor=balance,
        due_date=out.get("due_date", "1970-01-01"),
        as_of=as_of,
    )
    return out


def list_invoices(
    db: Database,
    *,
    as_of: date,
    customer_id: str | None = None,
    status: str | None = None,
    overdue_only: bool = False,
) -> list[dict[str, Any]]:
    query: dict[str, Any] = {}
    if customer_id:
        query["customer_id"] = customer_id
    if status:
        query["status"] = status
    items = [_serialize(d, as_of) for d in db["invoices"].find(query).sort("invoice_number", 1)]
    if overdue_only:
        items = [i for i in items if i["is_overdue"]]
    return items


def get_invoice(db: Database, invoice_number: str, *, as_of: date) -> dict[str, Any] | None:
    doc = db["invoices"].find_one({"invoice_number": invoice_number})
    return _serialize(doc, as_of) if doc else None


def list_open_sent(db: Database, *, currency: str | None = None) -> list[dict[str, Any]]:
    query: dict[str, Any] = {"status": "sent", "balance_due_minor": {"$gt": 0}}
    if currency:
        query["currency"] = currency
    return list(db["invoices"].find(query))
