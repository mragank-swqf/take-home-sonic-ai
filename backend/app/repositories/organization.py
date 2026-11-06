from typing import Any

from pymongo.database import Database


def get_organization(db: Database) -> dict[str, Any] | None:
    doc = db["organization"].find_one({"_id": "acme"})
    if not doc:
        return None
    doc["id"] = str(doc.pop("_id"))
    return doc
