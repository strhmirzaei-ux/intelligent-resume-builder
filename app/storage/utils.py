from __future__ import annotations

import json
import re
from datetime import UTC, date, datetime
from enum import Enum
from typing import Any
from uuid import UUID

from pydantic import BaseModel

STORAGE_SCHEMA_VERSION = 2
STORAGE_KEY_PATTERN = re.compile(r"^[A-Za-z0-9_-]{1,128}$")


def validate_storage_key(key: str) -> str:
    if not isinstance(key, str) or not STORAGE_KEY_PATTERN.fullmatch(key):
        raise ValueError("Storage key must contain only letters, digits, '_' or '-'.")
    return key


def parse_utc_timestamp(value: Any) -> datetime | None:
    if value is None:
        return None
    parsed = value if isinstance(value, datetime) else datetime.fromisoformat(str(value))
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=UTC)
    return parsed.astimezone(UTC)


def is_expired(value: Any, max_age_seconds: int | None) -> bool:
    if max_age_seconds is None:
        return False
    if not isinstance(max_age_seconds, int) or isinstance(max_age_seconds, bool) or max_age_seconds < 0:
        raise ValueError("max_age_seconds must be a non-negative integer")
    timestamp = parse_utc_timestamp(value)
    return timestamp is not None and (datetime.now(UTC) - timestamp).total_seconds() > max_age_seconds


def json_default(value: Any) -> Any:
    if isinstance(value, BaseModel):
        return value.model_dump(mode="json")
    if isinstance(value, (datetime, date)):
        return value.isoformat()
    if isinstance(value, UUID):
        return str(value)
    if isinstance(value, Enum):
        return value.value
    raise TypeError(f"Object of type {type(value).__name__} is not JSON serializable")


def validate_record(value: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise TypeError("Stored value must be a dictionary")
    if "resume" in value and not isinstance(value["resume"], dict):
        raise ValueError("Stored resume must be a dictionary")
    if "analysis" in value and not isinstance(value["analysis"], dict):
        raise ValueError("Stored analysis must be a dictionary")
    for field in ("messages", "questions"):
        if field in value and not isinstance(value[field], list):
            raise ValueError(f"Stored {field} must be a list")
    return value


def deduplicate_messages(messages: Any) -> list[dict[str, str]]:
    if not isinstance(messages, list):
        return []
    result: list[dict[str, str]] = []
    seen: set[tuple[str, str]] = set()
    for message in messages:
        if not isinstance(message, dict):
            continue
        role = str(message.get("role", "user"))
        content = str(message.get("content", ""))
        if not content or (role, content) in seen:
            continue
        seen.add((role, content))
        result.append({"role": role, "content": content})
    return result


def migrate_json_record(value: dict[str, Any]) -> dict[str, Any]:
    value = dict(value)
    version = int(value.get("schema_version", 1))
    if version < 2:
        value.setdefault("asked_deficiency_codes", [])
        value.setdefault("questions", [])
        for question in value["questions"]:
            if isinstance(question, dict):
                question.setdefault("target_entity", None)
        version = 2
    value.setdefault("conversation_summary", "")
    value.setdefault("suppressed_facts", [])
    value.setdefault("operation_history", [])
    value["schema_version"] = max(version, STORAGE_SCHEMA_VERSION)
    value["messages"] = deduplicate_messages(value.get("messages", []))
    return value


def validate_embedding(embedding: Any) -> list[float]:
    if not isinstance(embedding, (list, tuple)) or not embedding:
        raise ValueError("embedding must be a non-empty numeric sequence")
    try:
        values = [float(item) for item in embedding]
    except (TypeError, ValueError) as error:
        raise ValueError("embedding must contain only numbers") from error
    import math

    if not all(math.isfinite(item) for item in values):
        raise ValueError("embedding must contain only finite numbers")
    if math.sqrt(sum(item * item for item in values)) == 0:
        raise ValueError("embedding must not be a zero vector")
    return values


def dump_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, indent=2, default=json_default)
