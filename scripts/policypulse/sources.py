"""Fetchers for official public pages and feeds.

Each fetcher returns items that already include source, title, url, and date
when the page itself provided one. Failures are reported and do not stop
the other sources.
"""

from __future__ import annotations

import re
import sys
import xml.etree.ElementTree as ET
from html.parser import HTMLParser
from urllib.parse import urljoin

from .http import fetch_text
from .text import collapse, excerpt, has_devanagari, parse_date, stable_id, strip_html, today_ist

PIB_LIST = "https://www.pib.gov.in/allRel.aspx?reg=3&lang=1"
PIB_RSS = "https://pib.gov.in/RssMain.aspx?ModId=6&Lang=1&Regid=3"
RBI_PRESS = "https://rbi.org.in/pressreleases_rss.xml"
RBI_NOTIFICATIONS = "https://rbi.org.in/notifications_rss.xml"
SEBI_RSS = "https://www.sebi.gov.in/sebirss.xml"
SEBI_CIRCULARS = "https://www.sebi.gov.in/sebiweb/home/HomeAction.do?doListing=yes&sid=1&ssid=7&smid=0"
CBIC_TICKERS = "https://cbic-gst.gov.in/tickers.html"
DGFT_PAGES = [
    ("trade-notice", "DGFT trade notice", "https://www.dgft.gov.in/CP/?opt=trade-notice"),
    ("notification", "DGFT notification", "https://www.dgft.gov.in/CP/?opt=notification"),
    ("public-notice", "DGFT public notice", "https://www.dgft.gov.in/CP/?opt=public-notice"),
]
EGAZETTE = "https://egazette.gov.in/"


class SourceError(Exception):
    pass


def _item(**kwargs) -> dict:
    title = collapse(kwargs.get("title") or "")
    url = collapse(kwargs.get("url") or "")
    if not title or not url:
        raise ValueError("item needs a title and a source url")
    item_id = kwargs.get("id") or stable_id(kwargs.get("source") or "", url, title)
    return {
        "id": item_id,
        "source": kwargs["source"],
        "source_name": kwargs["source_name"],
        "feed": kwargs.get("feed") or kwargs["source"],
        "title": title,
        "url": url,
        "date": kwargs.get("date"),
        "date_precision": kwargs.get("date_precision") or ("published" if kwargs.get("date") else "missing"),
        "excerpt": excerpt(kwargs.get("excerpt") or "", 320),
        "instrument": collapse(kwargs.get("instrument") or ""),
        "body_name": collapse(kwargs.get("body_name") or ""),
        "language": kwargs.get("language") or ("hi" if has_devanagari(title) else "en"),
    }


def _rss_items(xml_text: str) -> list[ET.Element]:
    raw = xml_text.lstrip("\ufeff \r\n\t")
    start = raw.find("<")
    if start > 0:
        raw = raw[start:]
    root = ET.fromstring(raw.encode("utf-8"))
    return list(root.findall(".//item"))


def _child_text(item: ET.Element, tag: str) -> str:
    node = item.find(tag)
    if node is None or node.text is None:
        return ""
    return collapse(node.text)


def fetch_pib() -> list[dict]:
    items: dict[str, dict] = {}
    page = fetch_text(PIB_LIST)
    page_date = _pib_selected_date(page) or today_ist()
    for ministry, prid, title in _pib_links(page):
        url = f"https://www.pib.gov.in/PressReleaseDetail.aspx?PRID={prid}&lang=1"
        items[prid] = _item(
            id=f"pib-{prid}",
            source="pib",
            source_name="Press Information Bureau",
            feed="pib-english-listing",
            title=title,
            url=url,
            date=page_date,
            date_precision="published",
            instrument="PIB press release",
            body_name=ministry,
            language="en",
        )
    try:
        rss = fetch_text(PIB_RSS)
        for node in _rss_items(rss):
            title = _child_text(node, "title")
            link = _child_text(node, "link")
            prid_match = re.search(r"PRID=(\d+)", link, flags=re.I)
            if not title or not prid_match:
                continue
            prid = prid_match.group(1)
            url = f"https://www.pib.gov.in/PressReleaseDetail.aspx?PRID={prid}&lang=1"
            language = "hi" if has_devanagari(title) else "en"
            row = _item(
                id=f"pib-{prid}",
                source="pib",
                source_name="Press Information Bureau",
                feed="pib-rss",
                title=title,
                url=url,
                date=parse_date(_child_text(node, "pubDate")),
                date_precision="published" if parse_date(_child_text(node, "pubDate")) else "missing",
                instrument="PIB press release",
                language=language,
            )
            if prid in items:
                # Keep the English listing title and its date.
                existing = items[prid]
                if language == "hi":
                    existing["title_alt"] = title
                items[prid] = existing
            else:
                items[prid] = row
    except Exception:
        if not items:
            raise
    if not items:
        raise SourceError("PIB listing returned no releases")
    return list(items.values())


def _pib_selected_date(html: str) -> str | None:
    day = _selected_option(html, "ContentPlaceHolder1_ddlday")
    month = _selected_option(html, "ContentPlaceHolder1_ddlMonth")
    year = _selected_option(html, "ContentPlaceHolder1_ddlYear")
    if not (day and month and year) or day == "0":
        return None
    return parse_date(f"{int(day):02d}/{int(month):02d}/{year}")


def _selected_option(html: str, element_id: str) -> str | None:
    match = re.search(rf'id="{re.escape(element_id)}"[\s\S]*?</select>', html)
    if not match:
        return None
    selected = re.search(r'<option selected="selected" value="([^"]+)"', match.group(0))
    if selected:
        return selected.group(1)
    return None


def _pib_links(html: str) -> list[tuple[str, str, str]]:
    rows: list[tuple[str, str, str]] = []
    blocks = re.findall(
        r"<h3 class='font104'>([^<]*)</h3>\s*<ul class='num'>([\s\S]*?)</ul>",
        html,
    )
    for ministry, block in blocks:
        for prid, title in re.findall(
            r"href='/PressReleaseDetail\.aspx\?PRID=(\d+)'[^>]*>([^<]+)",
            block,
        ):
            rows.append((collapse(ministry), prid, collapse(title)))
    if rows:
        return rows
    for prid, title in re.findall(
        r'href="/PressReleaseDetail\.aspx\?PRID=(\d+)"[^>]*>([^<]+)',
        html,
    ):
        rows.append(("", prid, collapse(title)))
    return rows


def fetch_rbi() -> list[dict]:
    items = []
    items.extend(
        _rss_feed(
            RBI_PRESS,
            source="rbi",
            source_name="Reserve Bank of India",
            feed="rbi-press-releases",
            instrument="RBI press release",
        )
    )
    items.extend(
        _rss_feed(
            RBI_NOTIFICATIONS,
            source="rbi",
            source_name="Reserve Bank of India",
            feed="rbi-notifications",
            instrument="RBI notification",
        )
    )
    if not items:
        raise SourceError("RBI feeds returned no items")
    return items


def fetch_sebi() -> list[dict]:
    items = _rss_feed(
        SEBI_RSS,
        source="sebi",
        source_name="Securities and Exchange Board of India",
        feed="sebi-rss",
        instrument="SEBI update",
    )
    seen = {item["url"] for item in items}
    page = fetch_text(SEBI_CIRCULARS)
    for date_text, url, title in _sebi_circular_rows(page):
        if url in seen:
            continue
        seen.add(url)
        items.append(
            _item(
                source="sebi",
                source_name="Securities and Exchange Board of India",
                feed="sebi-circulars",
                title=title,
                url=url,
                date=parse_date(date_text),
                date_precision="published" if parse_date(date_text) else "missing",
                instrument="SEBI circular",
            )
        )
    if not items:
        raise SourceError("SEBI feeds returned no items")
    return items


def _sebi_circular_rows(html: str) -> list[tuple[str, str, str]]:
    rows = []
    for row_html in re.findall(r"<tr role='row'[\s\S]*?</tr>", html):
        link = re.search(r'href="(https://www\.sebi\.gov\.in[^"]+)"[^>]*>([\s\S]*?)</a>', row_html)
        if not link:
            continue
        date_match = re.search(r"<td[^>]*>\s*([^<]+?)\s*<", row_html)
        date_text = collapse(date_match.group(1)) if date_match else ""
        rows.append((date_text, link.group(1).strip(), strip_html(link.group(2))))
    return rows


def _rss_feed(url: str, source: str, source_name: str, feed: str, instrument: str) -> list[dict]:
    xml_text = fetch_text(url)
    rows = []
    for node in _rss_items(xml_text):
        title = strip_html(_child_text(node, "title"))
        link = _child_text(node, "link")
        if not title or not link:
            continue
        description = strip_html(_child_text(node, "description"))
        published = parse_date(_child_text(node, "pubDate"))
        rows.append(
            _item(
                source=source,
                source_name=source_name,
                feed=feed,
                title=title,
                url=link,
                date=published,
                date_precision="published" if published else "missing",
                excerpt=description,
                instrument=instrument,
            )
        )
    return rows


def fetch_cbic() -> list[dict]:
    html = fetch_text(CBIC_TICKERS)
    items = []
    seen: set[str] = set()
    chunks = re.findall(
        r"fa-angle-double-right[\s\S]*?<span[^>]*>([\s\S]*?)</span>",
        html,
    )
    for chunk in chunks:
        pdf = ""
        link = re.search(r'href="([^"]+\.pdf[^"]*)"', chunk, flags=re.I)
        if link:
            pdf = urljoin(CBIC_TICKERS, link.group(1).replace(" ", "%20"))
        text = strip_html(chunk)
        text = re.sub(r"\s*Please Click here for Advisory\.?\s*", " ", text, flags=re.I)
        text = collapse(text.strip(" \"“”"))
        if len(text) < 40 or text in seen:
            continue
        seen.add(text)
        published = parse_date(text)
        items.append(
            _item(
                id=stable_id("cbic", text),
                source="cbic",
                source_name="Central Board of Indirect Taxes and Customs",
                feed="cbic-gst-tickers",
                title=excerpt(text, 180),
                url=pdf or CBIC_TICKERS,
                date=published,
                date_precision="published" if published else "observed",
                excerpt=text,
                instrument="CBIC GST portal notice",
                body_name="CBIC",
            )
        )
    if not items:
        raise SourceError("CBIC ticker page returned no notices")
    return items


class _RowParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.rows: list[dict] = []
        self._in_cell = False
        self._cell: list[str] = []
        self._cells: list[str] = []
        self._href = ""
        self._in_row = False

    def handle_starttag(self, tag: str, attrs) -> None:
        attr = dict(attrs)
        if tag == "tr":
            self._in_row = True
            self._cells = []
            self._href = ""
        elif tag == "td" and self._in_row:
            self._in_cell = True
            self._cell = []
        elif tag == "a" and self._in_row and not self._href:
            href = attr.get("href") or ""
            if href and not href.startswith("javascript"):
                self._href = href

    def handle_endtag(self, tag: str) -> None:
        if tag == "td" and self._in_cell:
            self._cells.append(collapse("".join(self._cell)))
            self._in_cell = False
        elif tag == "tr" and self._in_row:
            if self._cells:
                self.rows.append({"cells": self._cells, "href": self._href})
            self._in_row = False

    def handle_data(self, data: str) -> None:
        if self._in_cell:
            self._cell.append(data)


def dgft_candidate_urls(opt: str) -> list[str]:
    """Primary listing plus fallbacks. Runners sometimes get 403 on only one host."""
    return [
        f"https://www.dgft.gov.in/CP/?opt={opt}",
        f"https://www.dgft.gov.in/CP/index.jsp?opt={opt}",
        f"https://dgft.gov.in/CP/?opt={opt}",
    ]


def dgft_listing_ok(html: str) -> bool:
    """A 200 block page has neither the PDF host nor the listing table."""
    text = html or ""
    return "content.dgft.gov.in" in text and "metaTable" in text


def _dgft_items_from_html(html: str, feed: str, instrument: str, seen: set[str]) -> list[dict]:
    parser = _RowParser()
    parser.feed(html)
    items = []
    for row in parser.rows:
        cells = row["cells"]
        href = row["href"]
        if len(cells) < 5 or not href or "content.dgft.gov.in" not in href:
            continue
        number, year, description, date_text = cells[1], cells[2], cells[3], cells[4]
        if not description or description.lower() == "description":
            continue
        if href in seen:
            continue
        seen.add(href)
        published = parse_date(date_text)
        label = f"{instrument} {number}".strip()
        if year:
            label = f"{label} ({year})"
        items.append(
            _item(
                id=stable_id("dgft", href),
                source="dgft",
                source_name="Directorate General of Foreign Trade",
                feed=f"dgft-{feed}",
                title=description,
                url=href,
                date=published,
                date_precision="published" if published else "missing",
                instrument=label,
                body_name="DGFT",
            )
        )
    return items


def fetch_dgft() -> list[dict]:
    items = []
    seen: set[str] = set()
    failures: list[str] = []
    # A homepage visit stores any session cookie before the listing requests.
    # Actions runners are often refused until that cookie exists.
    try:
        fetch_text("https://www.dgft.gov.in/", referer="https://www.dgft.gov.in/", retries=1, timeout=30)
    except Exception as exc:
        print(f"dgft warmup: {exc}", file=sys.stderr)
    for feed, instrument, _url in DGFT_PAGES:
        html = ""
        last_error: Exception | None = None
        for url in dgft_candidate_urls(feed):
            try:
                candidate = fetch_text(url, referer="https://www.dgft.gov.in/")
            except Exception as exc:
                last_error = exc
                print(f"dgft {feed} {url} failed: {exc}", file=sys.stderr)
                continue
            if not dgft_listing_ok(candidate):
                last_error = SourceError(f"{url} did not include the DGFT document table")
                print(f"dgft {feed} {url} rejected: not a document listing", file=sys.stderr)
                continue
            html = candidate
            break
        if not html:
            failures.append(f"{feed}: {last_error}")
            continue
        items.extend(_dgft_items_from_html(html, feed, instrument, seen))
    if not items:
        detail = "; ".join(failures) or "no documents"
        raise SourceError(f"DGFT pages returned no documents ({detail})")
    if failures:
        print(
            "dgft partial failure; keeping documents from the feeds that responded: "
            + "; ".join(failures),
            file=sys.stderr,
        )
    return items


def fetch_egazette() -> list[dict]:
    html = fetch_text(EGAZETTE)
    items = []
    specs = [
        ("Extraordinary", "rpt_Extra_lbl_MinistryE_", "rpt_Extra_lbl_SubjectE_", "rpt_Extra_lbl_DateE_", "rpt_Extra_lbl_UGIDExtra_"),
        ("Weekly", "rpt_Week_lbl_MinistryW_", "rpt_Week_lbl_SubjectW_", "rpt_Week_lbl_DateW_", "rpt_Week_lbl_UGIDWeekly_"),
    ]
    for kind, ministry_id, subject_id, date_id, ugid_id in specs:
        index = 0
        while True:
            gazette_id = _span(html, f"{ugid_id}{index}")
            if not gazette_id:
                break
            subject = _span(html, f"{subject_id}{index}") or kind
            ministry = _span(html, f"{ministry_id}{index}")
            published = parse_date(_span(html, f"{date_id}{index}"))
            title = collapse(f"{subject} [{gazette_id}]")
            items.append(
                _item(
                    id=stable_id("egazette", gazette_id),
                    source="egazette",
                    source_name="Gazette of India",
                    feed=f"egazette-{kind.lower()}",
                    title=title,
                    url=EGAZETTE,
                    date=published,
                    date_precision="published" if published else "missing",
                    excerpt=(
                        f"Gazette ID {gazette_id}. The eGazette homepage lists this "
                        f"{kind.lower()} issue. The PDF is the download control beside that ID."
                    ),
                    instrument=f"{kind} Gazette {gazette_id}",
                    body_name=ministry,
                )
            )
            index += 1
    if not items:
        raise SourceError("eGazette homepage returned no issues")
    return items


def _span(html: str, element_id: str) -> str:
    match = re.search(
        rf'id="{re.escape(element_id)}"[^>]*>([\s\S]*?)</span>',
        html,
    )
    return strip_html(match.group(1)) if match else ""


FETCHERS = [
    ("pib", "Press Information Bureau", PIB_LIST, fetch_pib),
    ("rbi", "Reserve Bank of India", RBI_PRESS, fetch_rbi),
    ("sebi", "SEBI", SEBI_RSS, fetch_sebi),
    ("cbic", "CBIC / GST", CBIC_TICKERS, fetch_cbic),
    ("dgft", "DGFT", DGFT_PAGES[0][2], fetch_dgft),
    ("egazette", "Gazette of India", EGAZETTE, fetch_egazette),
]
