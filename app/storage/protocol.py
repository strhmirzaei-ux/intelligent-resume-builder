from __future__ import annotations

from typing import Any, Protocol


class ResumeStore(Protocol):
    """Common persistence contract consumed by the resume pipeline."""

    semantic_search_supported: bool

    def get(self, key: str, max_age_seconds: int | None = None) -> dict[str, Any] | None:
        ...

    def put(self, key: str, value: dict[str, Any]) -> None:
        ...

    def delete(self, key: str) -> None:
        ...
