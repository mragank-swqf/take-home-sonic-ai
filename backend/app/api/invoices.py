from fastapi import APIRouter, HTTPException, Query

from app.core.db import get_db
from app.core.settings import get_settings
from app.repositories import invoices as invoices_repo

router = APIRouter(prefix="/api/invoices", tags=["invoices"])


@router.get("")
def list_invoices(
    customer_id: str | None = None,
    status: str | None = None,
    overdue: bool = Query(default=False),
) -> dict:
    as_of = get_settings().as_of_date()
    items = invoices_repo.list_invoices(
        get_db(),
        as_of=as_of,
        customer_id=customer_id,
        status=status,
        overdue_only=overdue,
    )
    return {"items": items, "as_of": as_of.isoformat()}


@router.get("/{invoice_number}")
def get_invoice(invoice_number: str) -> dict:
    as_of = get_settings().as_of_date()
    doc = invoices_repo.get_invoice(get_db(), invoice_number, as_of=as_of)
    if not doc:
        raise HTTPException(status_code=404, detail="Invoice not found")
    return doc
