from fastapi import APIRouter
from pydantic import BaseModel, Field

from app.core.db import get_db
from app.services import collections_inbox, reminders

router = APIRouter(prefix="/api/collections", tags=["collections"])


class ReminderBatchBody(BaseModel):
    customer_ids: list[str] | None = None


class ReminderForceBody(BaseModel):
    force: bool = True


class DraftBody(BaseModel):
    draft: str = Field(min_length=1)


class SendDraftBody(BaseModel):
    draft: str | None = None


@router.post("/reminders/send")
def send_reminders(body: ReminderBatchBody | None = None) -> dict:
    payload = body or ReminderBatchBody()
    return reminders.send_reminders(get_db(), customer_ids=payload.customer_ids, force=False)


@router.post("/reminders/send/{customer_id}")
def send_reminder_one(customer_id: str, body: ReminderForceBody | None = None) -> dict:
    force = True if body is None else body.force
    return reminders.send_reminders(get_db(), customer_ids=[customer_id], force=force)


@router.post("/inbox/check")
def check_inbox() -> dict:
    return collections_inbox.process_inbox_once()


@router.get("/conversations")
def conversations(status: str | None = None) -> dict:
    return {"items": collections_inbox.list_conversations(get_db(), status=status)}


@router.get("/conversations/{conversation_id}")
def conversation(conversation_id: str) -> dict:
    return collections_inbox.get_conversation(get_db(), conversation_id)


@router.get("/needs-attention")
def needs_attention() -> dict:
    return {"items": collections_inbox.list_needs_attention(get_db())}


@router.patch("/needs-attention/{conversation_id}")
def patch_needs_attention(conversation_id: str, body: DraftBody) -> dict:
    return collections_inbox.update_pending_draft(get_db(), conversation_id, body.draft)


@router.post("/needs-attention/{conversation_id}/send")
def send_needs_attention(conversation_id: str, body: SendDraftBody | None = None) -> dict:
    draft = body.draft if body else None
    return collections_inbox.send_needs_attention(get_db(), conversation_id, draft)
