import asyncio
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import collections, customers, demo, invoices, organization, reconciliation
from app.core.db import close_client, get_db
from app.core.settings import get_settings
from app.services.seed import seed_if_empty

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(_app: FastAPI):
    seed_if_empty(get_db())
    poll_task = asyncio.create_task(_imap_poll_loop())
    yield
    poll_task.cancel()
    close_client()


async def _imap_poll_loop() -> None:
    """Background IMAP poll; no-op until collections adapter is wired."""
    settings = get_settings()
    while True:
        try:
            from app.services import collections_inbox

            if settings.imap_host and settings.imap_user:
                await asyncio.to_thread(collections_inbox.process_inbox_once)
        except Exception:  # noqa: BLE001 — keep poller alive
            logger.exception("IMAP poll failed")
        await asyncio.sleep(max(5, settings.imap_poll_interval_seconds))


app = FastAPI(title="Sonic AI Take-Home API", version="0.1.0", lifespan=lifespan)

settings = get_settings()
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(demo.router)
app.include_router(organization.router)
app.include_router(customers.router)
app.include_router(invoices.router)
app.include_router(reconciliation.router)
app.include_router(collections.router)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}
