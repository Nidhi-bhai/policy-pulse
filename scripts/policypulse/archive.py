"""Growing archive. Items are merged by id and never dropped."""

from __future__ import annotations

import json
from pathlib import Path

from .text import now_ist

ROOT = Path(__file__).resolve().parents[2]
DATA = ROOT / "data"
ITEMS_PATH = DATA / "items.json"
ARCHIVE_DIR = DATA / "archive"
MANIFEST_PATH = DATA / "manifest.json"


def load_items() -> list[dict]:
    if not ITEMS_PATH.exists():
        return []
    payload = json.loads(ITEMS_PATH.read_text(encoding="utf-8"))
    if isinstance(payload, list):
        return payload
    return list(payload.get("items") or [])


def _nonempty(value) -> bool:
    if value is None:
        return False
    if isinstance(value, str):
        return bool(value.strip())
    if isinstance(value, (list, dict)):
        return bool(value)
    return True


def merge_item(old: dict | None, new: dict) -> dict:
    if old is None:
        merged = dict(new)
        merged["first_seen"] = new.get("first_seen") or new.get("fetched_at") or now_ist()
        return merged
    merged = dict(old)
    for key, value in new.items():
        if key == "first_seen":
            continue
        if key == "sectors" and value:
            merged["sectors"] = value
            continue
        if key == "title" and _nonempty(value):
            old_title = old.get("title") or ""
            # Prefer a Latin-script headline when the feed also has a Hindi one.
            if _looks_english(value) and not _looks_english(old_title):
                merged["title_alt"] = old_title
                merged["title"] = value
            elif _nonempty(old_title) and not _looks_english(value) and _looks_english(old_title):
                merged["title_alt"] = value
            else:
                merged["title"] = value
            continue
        if _nonempty(value):
            merged[key] = value
    merged["first_seen"] = old.get("first_seen") or new.get("fetched_at") or now_ist()
    return merged


def _looks_english(text: str) -> bool:
    letters = [ch for ch in text if ch.isalpha()]
    if not letters:
        return False
    latin = sum(1 for ch in letters if "A" <= ch <= "Z" or "a" <= ch <= "z")
    return latin / len(letters) > 0.6


def merge_all(existing: list[dict], fresh: list[dict]) -> list[dict]:
    by_id: dict[str, dict] = {}
    for item in existing:
        if item.get("id"):
            by_id[item["id"]] = item
    for item in fresh:
        item_id = item.get("id")
        if not item_id:
            continue
        by_id[item_id] = merge_item(by_id.get(item_id), item)
    items = list(by_id.values())
    items.sort(key=lambda row: (row.get("date") or "", row.get("first_seen") or ""), reverse=True)
    return items


def save_archive(items: list[dict], manifest: dict) -> None:
    DATA.mkdir(parents=True, exist_ok=True)
    ARCHIVE_DIR.mkdir(parents=True, exist_ok=True)
    updated = now_ist()
    payload = {"version": 1, "updated_at": updated, "item_count": len(items), "items": items}
    ITEMS_PATH.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    months: dict[str, list[dict]] = {}
    for item in items:
        month = (item.get("date") or item.get("first_seen") or "undated")[:7]
        months.setdefault(month, []).append(item)
    for month, rows in months.items():
        path = ARCHIVE_DIR / f"{month}.json"
        body = {"month": month, "item_count": len(rows), "items": rows}
        path.write_text(json.dumps(body, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    index = {
        "updated_at": updated,
        "item_count": len(items),
        "months": [
            {"month": month, "item_count": len(rows)}
            for month, rows in sorted(months.items(), reverse=True)
        ],
    }
    (ARCHIVE_DIR / "index.json").write_text(
        json.dumps(index, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    MANIFEST_PATH.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
