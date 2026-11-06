from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, EmailStr

from app.core.db import get_db
from app.repositories import customers as customers_repo

router = APIRouter(prefix="/api/customers", tags=["customers"])


class CustomerEmailUpdate(BaseModel):
    contact_email: EmailStr


@router.get("")
def list_customers() -> dict:
    return {"items": customers_repo.list_customers(get_db())}


@router.get("/{customer_id}")
def get_customer(customer_id: str) -> dict:
    doc = customers_repo.get_customer(get_db(), customer_id)
    if not doc:
        raise HTTPException(status_code=404, detail="Customer not found")
    return doc


@router.patch("/{customer_id}")
def patch_customer(customer_id: str, body: CustomerEmailUpdate) -> dict:
    try:
        doc = customers_repo.update_contact_email(get_db(), customer_id, str(body.contact_email))
    except ValueError as exc:
        if str(exc) == "email_taken":
            raise HTTPException(status_code=409, detail="Email already in use") from exc
        raise
    if not doc:
        raise HTTPException(status_code=404, detail="Customer not found")
    return doc
