from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from threading import Lock
from typing import Any


class JsonStore:
    def __init__(self, root: str = "data/sessions") -> None:
        self.root = Path(root)
        self.root.mkdir(parents=True, exist_ok=True)
        self._lock = Lock()

    def get(self, key: str, max_age_seconds: int | None = None) -> dict[str, Any] | None:
        path = self.root / f"{key}.json"
        if not path.exists():
            return None
        with self._lock, path.open("r", encoding="utf-8") as file:
            value = json.load(file)
        if max_age_seconds is not None and value.get("updated_at"):
            updated_at = datetime.fromisoformat(value["updated_at"])
            age = (datetime.now(UTC) - updated_at).total_seconds()
            if age > max_age_seconds:
                self.delete(key)
                return None
        return value

    def put(self, key: str, value: dict[str, Any]) -> None:
        value = dict(value)
        value["updated_at"] = datetime.now(UTC).isoformat()
        path = self.root / f"{key}.json"
        temporary = path.with_suffix(".tmp")
        with self._lock, temporary.open("w", encoding="utf-8") as file:
            json.dump(value, file, ensure_ascii=False, indent=2, default=str)
        temporary.replace(path)

    def delete(self, key: str) -> None:
        path = self.root / f"{key}.json"
        with self._lock:
            path.unlink(missing_ok=True)
