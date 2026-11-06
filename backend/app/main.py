from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.demo import router as demo_router
from app.core.db import close_client, get_db
from app.core.settings import get_settings
from app.services.seed import seed_if_empty


@asynccontextmanager
async def lifespan(_app: FastAPI):
    seed_if_empty(get_db())
    yield
    close_client()


app = FastAPI(title="Sonic AI Take-Home API", version="0.1.0", lifespan=lifespan)

settings = get_settings()
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(demo_router)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}
