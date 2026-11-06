from typing import Literal

from fastapi import APIRouter, File, UploadFile
from pydantic import BaseModel

from app.core.db import get_db
from app.core.settings import get_settings
from app.repositories import invoices as invoices_repo
from app.services import reconciliation as recon

router = APIRouter(prefix="/api/reconciliation", tags=["reconciliation"])


class ApproveBody(BaseModel):
    invoice_number: str | None = None
    tds_option: Literal["close", "leave_open"] | None = None


class ChooseBody(BaseModel):
    invoice_number: str


def _enrich(row: dict) -> dict:
    as_of = get_settings().as_of_date()
    inv_no = row.get("chosen_invoice_number") or row.get("suggested_invoice_number")
    inv = invoices_repo.get_invoice(get_db(), inv_no, as_of=as_of) if inv_no else None
    return {
        "id": row["id"],
        "upload_id": row["upload_id"],
        "txn_date": row["txn_date"],
        "narration": row["narration"],
        "reference": row.get("reference"),
        "amount_minor": row.get("credit_minor") or row.get("debit_minor") or 0,
        "credit_minor": row.get("credit_minor"),
        "debit_minor": row.get("debit_minor"),
        "currency": row["currency"],
        "direction": row["direction"],
        "match_status": row["match_status"],
        "suggested_invoice_number": row.get("suggested_invoice_number"),
        "suggested_score": row.get("suggested_score"),
        "reason": row.get("suggested_reason"),
        "candidates": row.get("candidates") or [],
        "ui_hints": row.get("ui_hints") or [],
        "chosen_invoice_number": row.get("chosen_invoice_number"),
        "tds_required": recon.tds_required_for_row(row, inv),
    }


@router.post("/uploads")
async def upload_statement(file: UploadFile = File(...)) -> dict:
    raw = await file.read()
    return recon.upload_csv(get_db(), filename=file.filename or "statement.csv", raw=raw)


@router.get("/uploads")
def list_uploads() -> dict:
    return {"items": recon.list_uploads(get_db())}


@router.get("/uploads/{upload_id}/suggestions")
def suggestions(upload_id: str) -> dict:
    rows = recon.get_suggestions(get_db(), upload_id)
    return {"items": [_enrich(r) for r in rows]}


@router.post("/rows/{row_id}/approve")
def approve(row_id: str, body: ApproveBody) -> dict:
    return recon.approve_row(
        get_db(),
        row_id,
        invoice_number=body.invoice_number,
        tds_option=body.tds_option,
    )


@router.post("/rows/{row_id}/reject")
def reject(row_id: str) -> dict:
    return recon.reject_row(get_db(), row_id)


@router.post("/rows/{row_id}/choose-invoice")
def choose(row_id: str, body: ChooseBody) -> dict:
    row = recon.choose_invoice(get_db(), row_id, body.invoice_number)
    return _enrich(row)
