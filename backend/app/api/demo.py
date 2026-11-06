from fastapi import APIRouter

from app.core.db import get_db
from app.repositories.customers import clear_reminder_cooldowns
from app.services.seed import reset_and_seed

router = APIRouter(prefix="/api/demo", tags=["demo"])


@router.post("/reset")
def reset_demo_data() -> dict:
    db = get_db()
    counts = reset_and_seed(db)
    clear_reminder_cooldowns(db)
    return {"ok": True, "seeded": counts}
