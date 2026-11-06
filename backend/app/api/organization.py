from fastapi import APIRouter, HTTPException

from app.core.db import get_db
from app.repositories import organization as org_repo

router = APIRouter(prefix="/api", tags=["organization"])


@router.get("/organization")
def get_organization() -> dict:
    doc = org_repo.get_organization(get_db())
    if not doc:
        raise HTTPException(status_code=404, detail="Organization not found")
    return doc
