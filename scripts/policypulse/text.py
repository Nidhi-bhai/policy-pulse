"""Text, date, and id helpers. No network."""

from __future__ import annotations

import hashlib
import re
import unicodedata
from datetime import datetime
from html.parser import HTMLParser
from zoneinfo import ZoneInfo

IST = ZoneInfo("Asia/Kolkata")

_MONTHS = {
    "jan": 1,
    "january": 1,
    "feb": 2,
    "february": 2,
    "mar": 3,
    "march": 3,
    "apr": 4,
    "april": 4,
    "may": 5,
    "jun": 6,
    "june": 6,
    "jul": 7,
    "july": 7,
    "aug": 8,
    "august": 8,
    "sep": 9,
    "sept": 9,
    "september": 9,
    "oct": 10,
    "october": 10,
    "nov": 11,
    "november": 11,
    "dec": 12,
    "december": 12,
}


class _TextExtractor(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.parts: list[str] = []
        self._skip = 0

    def handle_starttag(self, tag: str, attrs) -> None:
        if tag in {"script", "style"}:
            self._skip += 1
        if tag in {"p", "br", "tr", "div", "li", "h1", "h2", "h3"}:
            self.parts.append(" ")

    def handle_endtag(self, tag: str) -> None:
        if tag in {"script", "style"} and self._skip:
            self._skip -= 1

    def handle_data(self, data: str) -> None:
        if not self._skip:
            self.parts.append(data)


def strip_html(value: str) -> str:
    parser = _TextExtractor()
    try:
        parser.feed(value or "")
        parser.close()
    except Exception:
        return collapse(re.sub(r"<[^>]+>", " ", value or ""))
    return collapse("".join(parser.parts))


def collapse(value: str) -> str:
    value = unicodedata.normalize("NFKC", value or "")
    value = value.replace("\xa0", " ")
    return re.sub(r"\s+", " ", value).strip()


def has_devanagari(value: str) -> bool:
    return bool(re.search(r"[\u0900-\u097F]", value or ""))


def stable_id(*parts: str) -> str:
    raw = "\n".join(collapse(p) for p in parts if p)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:16]


def excerpt(value: str, limit: int = 320) -> str:
    text = collapse(value)
    if len(text) <= limit:
        return text
    cut = text[: limit - 1]
    if " " in cut:
        cut = cut.rsplit(" ", 1)[0]
    return cut.rstrip(" ,;:") + "…"


def mostly_numeric(value: str) -> bool:
    text = collapse(value)
    if len(text) < 40:
        return False
    digits = sum(ch.isdigit() for ch in text)
    return digits / len(text) > 0.22


def parse_date(value: str | None) -> str | None:
    """Return YYYY-MM-DD if a calendar date is present, else None.

    Numeric dates are read day-first, which is how these Indian notices are written.
    """
    if not value:
        return None
    text = collapse(value)
    text = re.sub(r"(\d+)(st|nd|rd|th)\b", r"\1", text, flags=re.I)
    iso = re.search(r"(\d{4})-(\d{2})-(\d{2})", text)
    if iso:
        return _valid(int(iso.group(1)), int(iso.group(2)), int(iso.group(3)))
    dmy = re.search(r"(\d{1,2})[./](\d{1,2})[./](\d{4})", text)
    if dmy:
        return _valid(int(dmy.group(3)), int(dmy.group(2)), int(dmy.group(1)))
    dashed = re.search(r"(\d{1,2})-([A-Za-z]{3,9})-(\d{4})", text)
    if dashed:
        month = _MONTHS.get(dashed.group(2).lower())
        if month:
            return _valid(int(dashed.group(3)), month, int(dashed.group(1)))
    word = re.search(r"(\d{1,2})\s+([A-Za-z]{3,9}),?\s+(\d{4})", text)
    if word:
        month = _MONTHS.get(word.group(2).lower())
        if month:
            return _valid(int(word.group(3)), month, int(word.group(1)))
    word2 = re.search(r"([A-Za-z]{3,9})\s+(\d{1,2}),?\s+(\d{4})", text)
    if word2:
        month = _MONTHS.get(word2.group(1).lower())
        if month:
            return _valid(int(word2.group(3)), month, int(word2.group(2)))
    return None


def _valid(year: int, month: int, day: int) -> str | None:
    try:
        return datetime(year, month, day).date().isoformat()
    except ValueError:
        return None


def today_ist() -> str:
    return datetime.now(IST).date().isoformat()


def now_ist() -> str:
    return datetime.now(IST).replace(microsecond=0).isoformat()


def format_display_date(iso_date: str | None) -> str:
    if not iso_date:
        return "Date not in source"
    try:
        parsed = datetime.strptime(iso_date, "%Y-%m-%d")
    except ValueError:
        return iso_date
    return parsed.strftime("%d %b %Y")
