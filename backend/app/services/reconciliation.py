from __future__ import annotations

import csv
import hashlib
import io
from datetime import datetime, timezone
from typing import Any

from bson import ObjectId
from fastapi import HTTPException
from pymongo.database import Database

from app.core.settings import get_settings
from app.repositories import customers as customers_repo
from app.repositories import invoices as invoices_repo
from app.services.dates import parse_iso_date
from app.services.money import to_minor
from app.services.reconciliation_match import assign_unique_suggestions, match_row

REQUIRED_HEADERS = ["txn_date", "narration", "reference", "credit", "debit", "currency"]
MAX_BYTES = 2 * 1024 * 1024
MAX_ROWS = 5000


def _serialize_row(doc: dict[str, Any]) -> dict[str, Any]:
    out = dict(doc)
    out["id"] = str(out.pop("_id"))
    out["upload_id"] = str(out["upload_id"])
    return out


def list_uploads(db: Database) -> list[dict[str, Any]]:
    items = []
    for doc in db["bank_statement_uploads"].find().sort("uploaded_at", -1):
        items.append(
            {
                "id": str(doc["_id"]),
                "filename": doc["filename"],
                "row_count": doc["row_count"],
                "uploaded_at": doc["uploaded_at"].isoformat(),
            }
        )
    return items


def get_suggestions(db: Database, upload_id: str) -> list[dict[str, Any]]:
    try:
        oid = ObjectId(upload_id)
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=404, detail="Upload not found") from exc
    if not db["bank_statement_uploads"].find_one({"_id": oid}):
        raise HTTPException(status_code=404, detail="Upload not found")
    rows = list(db["bank_statement_rows"].find({"upload_id": oid}).sort("row_index", 1))
    return [_serialize_row(r) for r in rows]


def upload_csv(db: Database, *, filename: str, raw: bytes) -> dict[str, Any]:
    if len(raw) > MAX_BYTES:
        raise HTTPException(status_code=413, detail="File too large (max 2MB)")
    if not filename.lower().endswith(".csv"):
        raise HTTPException(status_code=400, detail="Only .csv files are accepted")

    digest = hashlib.sha256(raw).hexdigest()
    if db["bank_statement_uploads"].find_one({"content_sha256": digest}):
        raise HTTPException(status_code=409, detail="Duplicate statement upload")

    org = db["organization"].find_one({"_id": "acme"}) or {}
    accepted = set(org.get("accepted_currencies") or ["INR", "USD", "EUR", "GBP"])

    try:
        text = raw.decode("utf-8-sig")
    except UnicodeDecodeError as exc:
        raise HTTPException(status_code=400, detail="CSV must be UTF-8") from exc

    reader = csv.DictReader(io.StringIO(text))
    if not reader.fieldnames:
        raise HTTPException(status_code=400, detail="Missing CSV header")
    headers = [h.strip() for h in reader.fieldnames]
    if headers != REQUIRED_HEADERS:
        raise HTTPException(
            status_code=400,
            detail=f"CSV headers must be exactly {REQUIRED_HEADERS}",
        )

    parsed_rows: list[dict[str, Any]] = []
    for idx, row in enumerate(reader):
        if idx >= MAX_ROWS:
            raise HTTPException(status_code=400, detail="Too many rows (max 5000)")
        try:
            txn_date = parse_iso_date(row["txn_date"].strip())
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=f"Row {idx}: bad txn_date") from exc
        currency = (row.get("currency") or "").strip().upper()
        if currency not in accepted:
            raise HTTPException(status_code=400, detail=f"Row {idx}: currency not accepted")
        credit_raw = (row.get("credit") or "").strip()
        debit_raw = (row.get("debit") or "").strip()
        if credit_raw and debit_raw:
            raise HTTPException(status_code=400, detail=f"Row {idx}: both credit and debit set")
        if not credit_raw and not debit_raw:
            raise HTTPException(status_code=400, detail=f"Row {idx}: credit and debit empty")
        credit_minor = to_minor(credit_raw) if credit_raw else None
        debit_minor = to_minor(debit_raw) if debit_raw else None
        direction = "credit" if credit_minor is not None else "debit"
        parsed_rows.append(
            {
                "row_index": idx,
                "txn_date": txn_date.isoformat(),
                "narration": (row.get("narration") or "").strip(),
                "reference": (row.get("reference") or "").strip(),
                "credit_minor": credit_minor,
                "debit_minor": debit_minor,
                "currency": currency,
                "direction": direction,
            }
        )

    customers = {c["customer_id"]: c for c in customers_repo.list_customers(db)}
    # raw docs for matching (need minor fields)
    open_invoices = list(
        db["invoices"].find({"status": "sent", "balance_due_minor": {"$gt": 0}})
    )

    match_outputs: list[dict[str, Any]] = []
    for prow in parsed_rows:
        if prow["direction"] == "debit":
            match_outputs.append(
                {
                    "suggested_invoice_number": None,
                    "suggested_score": None,
                    "reason": "Debit — not a customer receipt",
                    "candidates": [],
                    "ui_hints": [],
                    "match_status": "ignored",
                }
            )
            continue
        match_outputs.append(
            match_row(
                narration=prow["narration"],
                credit_minor=int(prow["credit_minor"]),
                currency=prow["currency"],
                txn_date=parse_iso_date(prow["txn_date"]),
                invoices=open_invoices,
                customers_by_id=customers,
                claimed_invoices=set(),
            )
        )

    match_outputs = assign_unique_suggestions(match_outputs)

    upload_id = db["bank_statement_uploads"].insert_one(
        {
            "filename": filename,
            "content_sha256": digest,
            "row_count": len(parsed_rows),
            "uploaded_at": datetime.now(timezone.utc),
        }
    ).inserted_id

    docs = []
    for prow, mout in zip(parsed_rows, match_outputs, strict=True):
        docs.append(
            {
                **prow,
                "upload_id": upload_id,
                "match_status": mout["match_status"],
                "suggested_invoice_number": mout["suggested_invoice_number"],
                "suggested_score": mout["suggested_score"],
                "suggested_reason": mout["reason"],
                "candidates": mout["candidates"],
                "ui_hints": mout["ui_hints"],
                "chosen_invoice_number": None,
                "tds_option": None,
            }
        )
    if docs:
        db["bank_statement_rows"].insert_many(docs)

    return {
        "upload_id": str(upload_id),
        "rows": len(docs),
        "suggestions_ready": True,
    }


def choose_invoice(db: Database, row_id: str, invoice_number: str) -> dict[str, Any]:
    row = _get_row(db, row_id)
    if row["match_status"] in {"approved", "rejected", "ignored"}:
        raise HTTPException(status_code=409, detail="Row cannot be modified")
    as_of = get_settings().as_of_date()
    inv = invoices_repo.get_invoice(db, invoice_number, as_of=as_of)
    if not inv:
        raise HTTPException(status_code=404, detail="Invoice not found")
    if inv["currency"] != row["currency"]:
        raise HTTPException(status_code=400, detail="Currency mismatch")
    if inv["status"] != "sent" or inv["balance_due_minor"] <= 0:
        raise HTTPException(status_code=400, detail="Invoice not open")
    db["bank_statement_rows"].update_one(
        {"_id": row["_id"]},
        {
            "$set": {
                "chosen_invoice_number": invoice_number,
                "match_status": "suggested",
            }
        },
    )
    return _serialize_row(db["bank_statement_rows"].find_one({"_id": row["_id"]}))


def reject_row(db: Database, row_id: str) -> dict[str, Any]:
    row = _get_row(db, row_id)
    if row["match_status"] == "approved":
        raise HTTPException(status_code=409, detail="Already approved")
    db["bank_statement_rows"].update_one(
        {"_id": row["_id"]},
        {"$set": {"match_status": "rejected"}},
    )
    return {"row_id": row_id, "match_status": "rejected"}


def approve_row(
    db: Database,
    row_id: str,
    *,
    invoice_number: str | None,
    tds_option: str | None,
) -> dict[str, Any]:
    row = _get_row(db, row_id)
    if row["direction"] != "credit":
        raise HTTPException(status_code=400, detail="Only credit rows can be approved")
    if row["match_status"] in {"approved", "rejected", "ignored"}:
        raise HTTPException(status_code=409, detail="Row not approvable")

    inv_no = invoice_number or row.get("chosen_invoice_number") or row.get("suggested_invoice_number")
    if not inv_no:
        raise HTTPException(status_code=400, detail="invoice_number required")

    inv_doc = db["invoices"].find_one({"invoice_number": inv_no})
    if not inv_doc:
        raise HTTPException(status_code=404, detail="Invoice not found")
    if inv_doc["status"] in {"paid", "draft"}:
        raise HTTPException(status_code=409, detail="Invoice not open for payment")
    if inv_doc["currency"] != row["currency"]:
        raise HTTPException(status_code=400, detail="Currency mismatch")

    credit = int(row["credit_minor"])
    balance = int(inv_doc["balance_due_minor"])
    total = int(inv_doc["total_minor"])
    paid = int(inv_doc["amount_paid_minor"])

    tds_closed = False
    note = None
    if credit < balance:
        if tds_option not in {"close", "leave_open"}:
            raise HTTPException(
                status_code=400,
                detail="Underpayment requires tds_option close|leave_open",
            )
        if tds_option == "close":
            new_paid = total
            new_balance = 0
            new_status = "paid"
            tds_closed = True
            apply_amount = credit
        else:
            new_paid = paid + credit
            new_balance = total - new_paid
            new_status = "paid" if new_balance <= 0 else "sent"
            apply_amount = credit
    elif credit == balance:
        new_paid = paid + credit
        new_balance = 0
        new_status = "paid"
        apply_amount = credit
    else:
        # overpay — apply up to balance
        apply_amount = balance
        new_paid = paid + balance
        new_balance = 0
        new_status = "paid"
        note = f"Overpayment of {credit - balance} minor units ignored for balance"

    db["invoices"].update_one(
        {"_id": inv_doc["_id"]},
        {
            "$set": {
                "amount_paid_minor": new_paid,
                "balance_due_minor": max(0, new_balance),
                "status": new_status,
            }
        },
    )
    payment_id = db["payments"].insert_one(
        {
            "invoice_number": inv_no,
            "customer_id": inv_doc["customer_id"],
            "amount_minor": apply_amount,
            "currency": row["currency"],
            "source": "bank_reconciliation",
            "bank_statement_row_id": row["_id"],
            "tds_closed": tds_closed,
            "approved_at": datetime.now(timezone.utc),
            "note": note,
        }
    ).inserted_id

    db["bank_statement_rows"].update_one(
        {"_id": row["_id"]},
        {
            "$set": {
                "match_status": "approved",
                "chosen_invoice_number": inv_no,
                "tds_option": tds_option,
            }
        },
    )

    as_of = get_settings().as_of_date()
    invoice_view = invoices_repo.get_invoice(db, inv_no, as_of=as_of)
    return {"payment_id": str(payment_id), "invoice": invoice_view}


def _get_row(db: Database, row_id: str) -> dict[str, Any]:
    try:
        oid = ObjectId(row_id)
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=404, detail="Row not found") from exc
    row = db["bank_statement_rows"].find_one({"_id": oid})
    if not row:
        raise HTTPException(status_code=404, detail="Row not found")
    return row


def tds_required_for_row(row: dict[str, Any], inv: dict[str, Any] | None) -> bool:
    if not inv or row.get("direction") != "credit" or row.get("credit_minor") is None:
        return False
    return int(row["credit_minor"]) < int(inv["balance_due_minor"])
