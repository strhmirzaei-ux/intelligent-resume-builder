from __future__ import annotations

from app.core.config import Settings
from app.storage.database_store import DatabaseStore
from app.storage.json_store import JsonStore


def build_store(settings: Settings):
    if settings.database_url:
        return DatabaseStore(
            settings.database_url,
            auto_create=settings.database_auto_create,
        )
    return JsonStore(settings.storage_path)
