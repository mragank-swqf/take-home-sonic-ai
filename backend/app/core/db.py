from pymongo import MongoClient
from pymongo.database import Database

from app.core.settings import get_settings

_client: MongoClient | None = None


def get_client() -> MongoClient:
    global _client
    if _client is None:
        settings = get_settings()
        _client = MongoClient(settings.mongo_uri)
    return _client


def get_db() -> Database:
    settings = get_settings()
    return get_client()[settings.mongo_db]


def close_client() -> None:
    global _client
    if _client is not None:
        _client.close()
        _client = None
