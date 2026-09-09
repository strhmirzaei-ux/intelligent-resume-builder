from datetime import UTC, datetime, timedelta
from pathlib import Path

from app.storage.json_store import JsonStore


def test_json_store_round_trip(tmp_path: Path):
    store = JsonStore(str(tmp_path))
    store.put("resume-1", {"value": "رزومه"})
    stored = store.get("resume-1")
    assert stored is not None
    assert stored["value"] == "رزومه"
    assert "updated_at" in stored
    store.delete("resume-1")
    assert store.get("resume-1") is None


def test_json_store_expires_old_records(tmp_path: Path):
    store = JsonStore(str(tmp_path))
    store.put("old", {"value": "قدیمی"})
    path = tmp_path / "old.json"
    value = store.get("old")
    assert value is not None
    value["updated_at"] = (datetime.now(UTC) - timedelta(seconds=10)).isoformat()
    path.write_text(__import__("json").dumps(value, ensure_ascii=False), encoding="utf-8")
    assert store.get("old", max_age_seconds=1) is None
    assert not path.exists()


def test_json_store_keeps_relative_root_under_project_root():
    store = JsonStore("data/sessions")
    assert store.root.name == "sessions"
    assert store.root.parent.name == "data"
