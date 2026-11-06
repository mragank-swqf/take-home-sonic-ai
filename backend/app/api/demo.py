from fastapi import APIRouter

from app.core.db import get_db
from app.services.seed import reset_and_seed

router = APIRouter(prefix="/api/demo", tags=["demo"])


@router.post("/reset")
def reset_demo_data() -> dict:
    counts = reset_and_seed(get_db())
    return {"ok": True, "seeded": counts}
