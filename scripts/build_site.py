#!/usr/bin/env python3
"""Build the static PolicyPulse site from data/items.json into docs/."""

from __future__ import annotations

import html
import json
import os
import re
import shutil
import sys
from datetime import date, datetime, timedelta
from email.utils import format_datetime
from pathlib import Path
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from policypulse.tagger import SECTORS, SECTOR_LABEL  # noqa: E402
from policypulse.text import format_display_date, today_ist  # noqa: E402

SITE = "https://nidhi-bhai.github.io/policy-pulse"
DOCS = ROOT / "docs"
WEB = ROOT / "web"
DATA = ROOT / "data" / "items.json"
MANIFEST = ROOT / "data" / "manifest.json"
IST = ZoneInfo("Asia/Kolkata")
# Notices dated before the week the site launched are the historical backfill.
BACKFILL_BEFORE = "2026-10-20"
DISCLAIMER = "PolicyPulse is not a government site. Verify every notice on the official source."
DIGEST_MAILTO = "mailto:nidhi69n@gmail.com?subject=PolicyPulse%20digest"
SLUG_FILE = WEB / "pro-slug.txt"

NAV = [
    ("index.html", "Latest"),
    ("sector/exports.html", "Exports"),
    ("sector/agri.html", "Agri"),
    ("sector/msme.html", "MSME"),
    ("sector/banking.html", "Banking"),
    ("sector/gst.html", "GST"),
    ("sector/pharma.html", "Pharma"),
    ("sector/startups.html", "Startups"),
    ("digest.html", "Daily digest"),
    ("pro.html", "Pro"),
]


def esc(value: object) -> str:
    return html.escape("" if value is None else str(value), quote=True)


def load() -> tuple[list[dict], dict]:
    payload = json.loads(DATA.read_text(encoding="utf-8"))
    items = payload["items"] if isinstance(payload, dict) else payload
    manifest = {}
    if MANIFEST.exists():
        manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    return items, manifest


def prefix(depth: int) -> str:
    return "../" * depth


def rel(depth: int, path: str) -> str:
    return prefix(depth) + path


def is_backfill(item: dict) -> bool:
    dated = item.get("date") or ""
    return bool(dated) and dated < BACKFILL_BEFORE


def chips(item: dict, depth: int) -> str:
    parts = []
    for slug in item.get("sectors") or []:
        label = SECTOR_LABEL.get(slug, slug)
        parts.append(
            f'<a class="chip {esc(slug)}" href="{esc(rel(depth, f"sector/{slug}.html"))}">{esc(label)}</a>'
        )
    if is_backfill(item):
        parts.append('<span class="chip backfill">Backfill</span>')
    return "".join(parts)


def card(item: dict, depth: int) -> str:
    dek = item.get("what_changed") or ""
    if len(dek) > 240:
        dek = dek[:237].rsplit(" ", 1)[0] + "…"
    return f"""
<article class="card" data-source="{esc(item.get("source"))}">
  <div class="meta">
    <time datetime="{esc(item.get("date") or "")}">{esc(format_display_date(item.get("date")))}</time>
    <span class="src">{esc(item.get("source_name"))}</span>
  </div>
  <h2><a href="{esc(rel(depth, f"items/{item['id']}.html"))}">{esc(item.get("title"))}</a></h2>
  <p class="dek">{esc(dek)}</p>
  <div class="chips">{chips(item, depth)}</div>
</article>"""


def shell(
    title: str,
    description: str,
    depth: int,
    current: str,
    body: str,
    canonical_path: str,
    robots: str | None = None,
) -> str:
    pre = prefix(depth)
    nav = []
    for path, label in NAV:
        current_attr = ' aria-current="page"' if path == current else ""
        nav.append(f'<a href="{esc(rel(depth, path))}"{current_attr}>{esc(label)}</a>')
    canonical = SITE + canonical_path
    robots_tag = f'  <meta name="robots" content="{esc(robots)}">\n' if robots else ""
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{esc(title)}</title>
  <meta name="description" content="{esc(description)}">
{robots_tag}  <link rel="canonical" href="{esc(canonical)}">
  <meta property="og:title" content="{esc(title)}">
  <meta property="og:description" content="{esc(description)}">
  <meta property="og:url" content="{esc(canonical)}">
  <meta property="og:type" content="website">
  <link rel="alternate" type="application/rss+xml" title="PolicyPulse" href="{esc(rel(depth, "feed.xml"))}">
  <link rel="icon" href="{esc(pre)}assets/favicon.svg" type="image/svg+xml">
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
  <link href="https://fonts.googleapis.com/css2?family=Figtree:wght@400;560;680&family=Fraunces:opsz,wght@9..144,560;9..144,680&display=swap" rel="stylesheet">
  <link rel="stylesheet" href="{esc(pre)}assets/style.css">
</head>
<body>
  <a class="skip" href="#main">Skip to content</a>
  <header class="top">
    <div class="brand">
      <a href="{esc(rel(depth, "index.html"))}"><span class="mark">P</span>PolicyPulse</a>
      <p>Indian policy, in business English</p>
    </div>
    <nav>{"".join(nav)}</nav>
  </header>
  <main id="main" class="wrap">
    {body}
  </main>
  <footer class="foot">
    <p>Built by <a href="https://github.com/Nidhi-bhai">Nidhi Karuturi</a>. Briefs quote official headlines and never replace the source.</p>
    <p>
      <a href="{esc(rel(depth, "about.html"))}">About</a> ·
      <a href="{esc(rel(depth, "sources.html"))}">Sources</a> ·
      <a href="{esc(rel(depth, "archive.html"))}">Archive</a> ·
      <a href="{esc(rel(depth, "feed.xml"))}">RSS</a> ·
      <a href="{esc(rel(depth, "sitemap.xml"))}">Sitemap</a>
    </p>
  </footer>
  <script src="{esc(pre)}config.js"></script>
  <script src="{esc(pre)}assets/site.js"></script>
</body>
</html>
"""


def page_home(items: list[dict], manifest: dict) -> str:
    latest = items[:40]
    families = manifest.get("source_families") or sorted({item["source"] for item in items})
    updated = (manifest.get("generated_at") or "")[:10]
    filters = ['<button type="button" data-filter="all" class="is-on">All</button>']
    names = {
        "pib": "PIB",
        "rbi": "RBI",
        "sebi": "SEBI",
        "cbic": "CBIC",
        "dgft": "DGFT",
        "egazette": "Gazette",
    }
    for source in ("pib", "rbi", "sebi", "cbic", "dgft", "egazette"):
        if any(item["source"] == source for item in latest):
            filters.append(f'<button type="button" data-filter="{source}">{names[source]}</button>')
    cards = "\n".join(card(item, 0) for item in latest)
    body = f"""
<section class="hero">
  <div>
    <p class="eyebrow">Latest feed · {esc(format_display_date(updated) if updated else "archive")}</p>
    <h1>What changed, who it touches, and what to read next.</h1>
    <p class="lede">PolicyPulse turns public Indian government notices into a short business brief for MSMEs, traders, exporters, and investors. Every card links the official source. The wording is taken from that source, not from a guess. The public feed updates daily. Pro is a weekly brief.</p>
    <p>The archive includes a 2023–26 backfill. Notices are labeled with the date on the official document, not the day they were added.</p>
    <p class="disclaimer">{DISCLAIMER}</p>
  </div>
  <dl class="stats">
    <div><dt>Items in the archive</dt><dd>{len(items)}</dd></div>
    <div><dt>Official sources</dt><dd>{len(families)}</dd></div>
    <div><dt>On this page</dt><dd>{len(latest)}</dd></div>
    <div><dt>Price of Pro</dt><dd>$9</dd></div>
  </dl>
</section>
<div class="filters">{"".join(filters)}</div>
<div class="feed">{cards}</div>
"""
    return shell(
        "PolicyPulse — Indian policy in business English",
        "Plain-English business impact of Indian government policy changes for MSMEs, traders, exporters, and investors.",
        0,
        "index.html",
        body,
        "/",
    )


def page_sector(slug: str, label: str, items: list[dict]) -> str:
    rows = [item for item in items if slug in (item.get("sectors") or [])]
    cards = "\n".join(card(item, 1) for item in rows) or "<p class=\"note\">No item in the archive has matched this sector's keywords yet.</p>"
    body = f"""
<header class="page-head">
  <p class="eyebrow">Sector</p>
  <h1>{esc(label)}</h1>
  <p class="lede">{len(rows)} archived notices whose official text matched this sector's keyword list. Open the source before you act.</p>
</header>
<div class="feed">{cards}</div>
"""
    return shell(
        f"{label} policy briefs — PolicyPulse",
        f"Indian government notices tagged {label}, with a plain-English reading aid and a link to the official source.",
        1,
        f"sector/{slug}.html",
        body,
        f"/sector/{slug}.html",
    )


def page_item(item: dict) -> str:
    title = item.get("title") or "Policy notice"
    description = (item.get("what_changed") or title)[:180]
    llm = ""
    if item.get("llm_summary"):
        llm = f"""
<section class="panel">
  <h2>Optional model note</h2>
  <p>{esc(item["llm_summary"])}</p>
  <p class="note">This note was produced only because a model key was configured, and it was kept only if it did not add a number missing from the source text. The rule-based brief above still stands.</p>
</section>"""
    date_note = ""
    if item.get("date_precision") == "observed":
        date_note = "<p class=\"note\">The source page did not give a publication date. The date shown is a date found inside the notice text, or the day PolicyPulse stored it.</p>"
    elif item.get("date_precision") == "missing":
        date_note = "<p class=\"note\">This feed did not include a publication date.</p>"
    elif is_backfill(item):
        date_note = "<p class=\"note\">Backfill. This date is the date on the official document, not the day PolicyPulse added the notice. The archive includes a 2023–26 backfill.</p>"
    alt = ""
    if item.get("title_alt"):
        alt = f"<p class=\"note\">Same release, other language on the official feed: {esc(item['title_alt'])}</p>"
    ld = {
        "@context": "https://schema.org",
        "@type": "NewsArticle",
        "headline": title,
        "datePublished": item.get("date") or (item.get("first_seen") or "")[:10],
        "description": description,
        "isBasedOn": item.get("url"),
        "citation": item.get("url"),
        "author": {"@type": "Organization", "name": "PolicyPulse"},
        "publisher": {"@type": "Organization", "name": "PolicyPulse"},
    }
    ld_json = json.dumps(ld, ensure_ascii=False).replace("<", "\\u003c")
    body = f"""
<header class="page-head">
  <p class="eyebrow">{esc(item.get("source_name"))} · {esc(format_display_date(item.get("date")))}</p>
  <h1>{esc(title)}</h1>
  {alt}
  <p><a class="button solid" href="{esc(item.get("url"))}">Read the official source</a></p>
  {date_note}
  <div class="chips">{chips(item, 1)}</div>
</header>
<section class="panel">
  <h2>What changed</h2>
  <p>{esc(item.get("what_changed"))}</p>
</section>
<section class="panel">
  <h2>Who is affected</h2>
  <p>{esc(item.get("who_affected"))}</p>
</section>
<section class="panel">
  <h2>Likely business impact and action</h2>
  <p>{esc(item.get("impact"))}</p>
  <p>{esc(item.get("action"))}</p>
</section>
{llm}
<section class="panel">
  <h2>How this page was written</h2>
  <p>Basis: {esc(item.get("basis") or "keyword-rules")}. PolicyPulse stores the official title, the source URL, and the date the source gave. It does not invent rates, deadlines, or legal effects. If a keyword such as “amendment” or “export” is absent, the matching sentence is absent too.</p>
  <p class="note">Instrument: {esc(item.get("instrument") or "—")}. Feed: {esc(item.get("feed") or item.get("source"))}.</p>
</section>
<script type="application/ld+json">{ld_json}</script>
"""
    return shell(
        f"{title} — PolicyPulse",
        description,
        1,
        "",
        body,
        f"/items/{item['id']}.html",
    )


def page_archive(items: list[dict]) -> str:
    groups: dict[str, list[dict]] = {}
    for item in items:
        month = (item.get("date") or "undated")[:7]
        groups.setdefault(month, []).append(item)
    blocks = []
    for month, rows in groups.items():
        lis = []
        for item in rows:
            item_href = rel(0, "items/" + item["id"] + ".html")
            lis.append(
                "<li><time datetime=\"%s\">%s</time> "
                "<a href=\"%s\">%s</a> "
                "<span class=\"note\">· %s</span></li>"
                % (
                    esc(item.get("date") or ""),
                    esc(format_display_date(item.get("date"))),
                    esc(item_href),
                    esc(item.get("title")),
                    esc(item.get("source_name")),
                )
            )
        blocks.append(f'<section class="month"><h2>{esc(month)}</h2><ul class="list">{"".join(lis)}</ul></section>')
    body = f"""
<header class="page-head">
  <p class="eyebrow">History</p>
  <h1>The archive is the record.</h1>
  <p class="lede">{len(items)} notices kept with their source URL and date. The public feed updates daily. Daily runs add items and keep old ones. The archive includes a 2023–26 backfill, and each notice is labeled with the date on the official document. Month files live in the repository under <code>data/archive/</code>.</p>
</header>
{"".join(blocks)}
"""
    return shell(
        "Archive — PolicyPulse",
        "Growing archive of Indian government policy notices with source links.",
        0,
        "",
        body,
        "/archive.html",
    )


def page_about() -> str:
    body = """
<header class="page-head">
  <p class="eyebrow">Method</p>
  <h1>A reading aid, tied to the source.</h1>
</header>
<div class="prose">
  <p>PolicyPulse is a static site. A daily GitHub Actions job downloads public pages from PIB, RBI, SEBI, CBIC, DGFT, and the Gazette of India, stores each notice as JSON, and rebuilds these pages.</p>
  <p>The brief for each notice has three parts: what the official text says, which sector keywords matched, and a next step that tells you to open the source. Sentences about restriction, amendment, timelines, banking instruments, duties, or licences appear only when those words are in the official text.</p>
  <p>An optional language model can add a note when the repository secret <code>POLICYPULSE_LLM_API_KEY</code> is set. The site builds and reads correctly with that secret unset. A model note is dropped if it contains a number that was not in the source text.</p>
  <p>This is not a government website and not legal, tax, or investment advice.</p>
</div>
"""
    return shell(
        "About — PolicyPulse",
        "How PolicyPulse turns official Indian government notices into plain-English business briefs.",
        0,
        "",
        body,
        "/about.html",
    )


def page_sources(manifest: dict) -> str:
    rows = []
    for source in manifest.get("sources") or []:
        status = "Fetched" if source.get("ok") else "Failed"
        rows.append(
            f"<li><strong>{esc(source.get('name'))}</strong> — {esc(status)}, "
            f"{esc(source.get('fetched'))} items. <a href=\"{esc(source.get('url'))}\">{esc(source.get('url'))}</a>"
            f"{'' if source.get('ok') else ' — ' + esc(source.get('error'))}</li>"
        )
    extra = "".join(rows) or "<li>Run the ingest job to record source status.</li>"
    body = f"""
<header class="page-head">
  <p class="eyebrow">Sources</p>
  <h1>Official public pages only.</h1>
</header>
<ul class="list">
  <li><a href="https://www.pib.gov.in/allRel.aspx?reg=3&lang=1">PIB English press-release listing</a> and the <a href="https://pib.gov.in/RssMain.aspx?ModId=6&Lang=1&Regid=3">PIB press-release RSS</a>.</li>
  <li><a href="https://rbi.org.in/pressreleases_rss.xml">RBI press releases RSS</a> and <a href="https://rbi.org.in/notifications_rss.xml">RBI notifications RSS</a>.</li>
  <li><a href="https://www.sebi.gov.in/sebirss.xml">SEBI RSS</a> and the <a href="https://www.sebi.gov.in/sebiweb/home/HomeAction.do?doListing=yes&sid=1&ssid=7&smid=0">SEBI circulars listing</a>.</li>
  <li><a href="https://cbic-gst.gov.in/tickers.html">CBIC GST portal tickers</a>, the public notice board for GST and central excise updates.</li>
  <li><a href="https://www.dgft.gov.in/CP/?opt=trade-notice">DGFT trade notices</a>, <a href="https://www.dgft.gov.in/CP/?opt=notification">notifications</a>, and <a href="https://www.dgft.gov.in/CP/?opt=public-notice">public notices</a>.</li>
  <li><a href="https://egazette.gov.in/">eGazette homepage</a> recent extraordinary and weekly issues. The PDF is the download control next to the gazette ID.</li>
</ul>
<h2>Last ingest</h2>
<ul class="list">{extra}</ul>
"""
    return shell(
        "Sources — PolicyPulse",
        "Official public feeds and pages PolicyPulse reads.",
        0,
        "",
        body,
        "/sources.html",
    )


def page_digest() -> str:
    options = "".join(
        f'<option value="{esc(slug)}">{esc(label)}</option>' for slug, label in SECTORS
    )
    body = f"""
<header class="page-head">
  <p class="eyebrow">Free</p>
  <h1>Daily digest signup.</h1>
  <p class="lede">The public feed updates daily. This form opens an email draft so you can ask for that digest. Set <code>DIGEST_FORM_ACTION</code> in <code>config.js</code> when you want the form to post to a Google Form instead.</p>
</header>
<p id="digest-mode" class="note">Submitting opens an email draft to request the free daily digest.</p>
<form id="digest-form" class="panel" method="post" action="{esc(DIGEST_MAILTO)}" enctype="text/plain">
  <label for="email">Email</label>
  <input id="email" name="email" type="email" required autocomplete="email" placeholder="name@company.in">
  <label for="sector">Sector you care about</label>
  <select id="sector" name="sector">{options}</select>
  <p><button class="button solid" type="submit">Request the free daily digest</button></p>
</form>
"""
    return shell(
        "Daily digest — PolicyPulse",
        "Sign up for a free daily PolicyPulse digest.",
        0,
        "digest.html",
        body,
        "/digest.html",
    )


def page_pro() -> str:
    body = f"""
<header class="page-head">
  <p class="eyebrow">Pro · $9/month</p>
  <h1>Weekly sector brief.</h1>
  <p class="lede">The public feed updates daily. Pro is a weekly brief every Monday, at your private link. PayPal shows that link after you subscribe. Bookmark it. Card numbers never touch this repository.</p>
  <p class="disclaimer">{DISCLAIMER}</p>
</header>
<section class="panel">
  <h2>What you are paying for</h2>
  <p>Delivery is a weekly brief every Monday, at your private link. Each edition is a per-sector digest of that week's notices, with the impact note and the official source. The underlying notices stay free on this site.</p>
  <p>The private page is unlisted. A new edition starts every Monday and is refreshed when the daily archive run picks up notices dated in that week.</p>
  <label for="pro-email">Email (optional)</label>
  <input id="pro-email" name="email" type="email" autocomplete="email" placeholder="name@company.in">
  <p class="note">Checkout works with this field left blank. If a form URL is set in <code>config.js</code>, PolicyPulse sends the subscription id and this email to that form after PayPal approves. With no form URL, the email is not sent anywhere.</p>
  <div id="paypal-button"></div>
  <p id="paypal-status" class="note"></p>
</section>
"""
    return shell(
        "Pro weekly brief — PolicyPulse",
        "PolicyPulse Pro weekly sector brief at $9 per month via PayPal.",
        0,
        "pro.html",
        body,
        "/pro.html",
    )


def write_rss(items: list[dict]) -> str:
    chunks = [
        '<?xml version="1.0" encoding="UTF-8"?>',
        '<rss version="2.0">',
        "<channel>",
        "<title>PolicyPulse</title>",
        f"<link>{SITE}/</link>",
        "<description>Plain-English business impact of Indian government policy changes, each item linked to its official source.</description>",
        "<language>en-in</language>",
    ]
    for item in items[:50]:
        link = f"{SITE}/items/{item['id']}.html"
        pub = _rss_date(item.get("date") or (item.get("first_seen") or "")[:10])
        description = (
            f"{item.get('what_changed', '')} Official source: {item.get('url', '')}"
        )
        chunks.append("<item>")
        chunks.append(f"<title>{esc(item.get('title'))}</title>")
        chunks.append(f"<link>{esc(link)}</link>")
        chunks.append(f"<guid isPermaLink=\"true\">{esc(link)}</guid>")
        if pub:
            chunks.append(f"<pubDate>{esc(pub)}</pubDate>")
        chunks.append(f"<description>{esc(description)}</description>")
        chunks.append("</item>")
    chunks.append("</channel></rss>\n")
    return "\n".join(chunks)


def _rss_date(iso_date: str) -> str:
    if not iso_date or len(iso_date) < 10:
        return ""
    try:
        parsed = datetime.strptime(iso_date[:10], "%Y-%m-%d").replace(tzinfo=IST)
    except ValueError:
        return ""
    return format_datetime(parsed)


_SLUG_RE = re.compile(r"[A-Za-z0-9_-]{16,}")


def load_pro_slug() -> str:
    """Committed random constant, unless POLICYPULSE_PRO_SLUG is set for this run."""
    env = os.environ.get("POLICYPULSE_PRO_SLUG", "").strip()
    raw = env or SLUG_FILE.read_text(encoding="utf-8").strip()
    if not _SLUG_RE.fullmatch(raw):
        raise SystemExit(
            "Pro slug must match [A-Za-z0-9_-]{16,} (POLICYPULSE_PRO_SLUG or web/pro-slug.txt)"
        )
    return raw


def iso_week_key(iso_date: str) -> str | None:
    try:
        parsed = datetime.strptime((iso_date or "")[:10], "%Y-%m-%d").date()
    except ValueError:
        return None
    year, week, _weekday = parsed.isocalendar()
    return f"{year}-W{week:02d}"


def week_bounds(week_key: str) -> tuple[date, date]:
    year_text, week_text = week_key.split("-W", 1)
    monday = date.fromisocalendar(int(year_text), int(week_text), 1)
    return monday, monday + timedelta(days=6)


def current_iso_week(today: str | None = None) -> str:
    key = iso_week_key(today or today_ist())
    if not key:
        raise SystemExit("could not resolve the current ISO week")
    return key


def group_by_iso_week(items: list[dict]) -> dict[str, list[dict]]:
    """Dated notices only. Undated rows are omitted so they are not given a fake week."""
    groups: dict[str, list[dict]] = {}
    for item in items:
        dated = item.get("date") or ""
        if len(dated) < 10:
            continue
        key = iso_week_key(dated)
        if not key:
            continue
        groups.setdefault(key, []).append(item)
    for rows in groups.values():
        rows.sort(key=lambda row: row.get("date") or "", reverse=True)
    return groups


def robots_txt(pro_slug: str) -> str:
    return (
        "User-agent: *\n"
        "Allow: /\n"
        f"Disallow: /policy-pulse/pro/{pro_slug}/\n"
        f"Disallow: /pro/{pro_slug}/\n"
        "Sitemap: " + SITE + "/sitemap.xml\n"
    )


def _config_string(text: str, key: str, default: str = "") -> str:
    match = re.search(rf"{re.escape(key)}\s*:\s*(\"(?:\\.|[^\"\\])*\"|'[^']*')", text)
    if not match:
        return default
    literal = match.group(1)
    if literal.startswith('"'):
        return json.loads(literal)
    return literal[1:-1]


def render_config(existing: str, pro_slug: str) -> str:
    """Rewrite public config. Keeps the live PayPal ids and any configured form URL."""
    paypal = _config_string(existing, "PAYPAL_CLIENT_ID")
    plan = _config_string(existing, "PLAN_ID")
    digest_action = _config_string(existing, "DIGEST_FORM_ACTION")
    pro_action = _config_string(existing, "PRO_FORM_ACTION")
    email_field = _config_string(existing, "PRO_FORM_EMAIL_FIELD", "email") or "email"
    sub_field = _config_string(existing, "PRO_FORM_SUBSCRIPTION_FIELD", "subscription_id") or "subscription_id"
    lines = [
        "// Public site config. Do not put secrets in this file.",
        "// PayPal subscription buttons read PAYPAL_CLIENT_ID and PLAN_ID at runtime.",
        "// The client id is public. The PayPal secret never goes here.",
        "window.POLICY_PULSE_CONFIG = {",
        f"  PAYPAL_CLIENT_ID: {json.dumps(paypal)},",
        f"  PLAN_ID: {json.dumps(plan)},",
        "  // Optional. When set, the daily digest form posts here instead of opening mail.",
        f"  DIGEST_FORM_ACTION: {json.dumps(digest_action)},",
        f"  DIGEST_MAILTO: {json.dumps(DIGEST_MAILTO)},",
        "  // Unlisted weekly brief. Revealed after PayPal approves. Kept out of the sitemap.",
        f"  PRO_BRIEF_PATH: {json.dumps('pro/' + pro_slug + '/')},",
        "  // Optional Google Form action. Empty skips the subscription email post.",
        f"  PRO_FORM_ACTION: {json.dumps(pro_action)},",
        f"  PRO_FORM_EMAIL_FIELD: {json.dumps(email_field)},",
        f"  PRO_FORM_SUBSCRIPTION_FIELD: {json.dumps(sub_field)}",
        "};",
        "",
    ]
    return "\n".join(lines)


def page_brief(
    rows: list[dict],
    week_key: str,
    monday: date,
    sunday: date,
    pro_slug: str,
    current: bool,
    earlier: list[str] | None = None,
) -> str:
    depth = 2
    sections = []
    buckets: list[tuple[str, str]] = list(SECTORS)
    buckets.append(("", "Not matched to a sector keyword"))
    for slug, label in buckets:
        if slug:
            chosen = [item for item in rows if slug in (item.get("sectors") or [])]
        else:
            chosen = [item for item in rows if not (item.get("sectors") or [])]
        if not chosen:
            continue
        blocks = []
        for item in chosen:
            item_href = rel(depth, f"items/{item['id']}.html")
            blocks.append(
                "<article class=\"brief-item\">"
                f"<p class=\"meta\"><time datetime=\"{esc(item.get('date') or '')}\">{esc(format_display_date(item.get('date')))}</time> "
                f"<span class=\"src\">{esc(item.get('source_name'))}</span></p>"
                f"<h3><a href=\"{esc(item_href)}\">{esc(item.get('title'))}</a></h3>"
                f"<p>{esc(item.get('impact') or '')}</p>"
                f"<p class=\"action\"><a href=\"{esc(item_href)}\">Brief on PolicyPulse</a> · "
                f"<a href=\"{esc(item.get('url'))}\">Official source</a></p>"
                "</article>"
            )
        sections.append(
            f"<section class=\"brief-sector\"><h2>{esc(label)}</h2>{''.join(blocks)}</section>"
        )
    if current and earlier:
        links = "".join(
            f'<li><a href="{esc(key)}.html">{esc(key)}</a></li>' for key in sorted(earlier, reverse=True)[:16]
        )
        sections.append(f"<section class=\"brief-sector\"><h2>Earlier editions</h2><ul class=\"list\">{links}</ul></section>")
    if sections:
        body_sections = "".join(sections)
    else:
        body_sections = (
            "<p class=\"note\">No dated notice in the archive falls in this Monday–Sunday week yet. "
            "The daily run fills this page when a source publishes a date in the week.</p>"
        )
    span = f"{monday.strftime('%d %b %Y')}–{sunday.strftime('%d %b %Y')}"
    if current:
        edition = (
            f"This is the current week, {span}. "
            "A new edition starts every Monday and is refreshed by the daily archive run. Bookmark this page. "
            "Delivery is a weekly brief every Monday, at your private link."
        )
    else:
        edition = (
            f"Edition for the week of {span}. "
            "Delivery is a weekly brief every Monday, at your private link."
        )
    body = f"""
<header class="page-head">
  <p class="eyebrow">Pro brief · {esc(week_key)}</p>
  <h1>Weekly brief</h1>
  <p class="lede">{esc(edition)}</p>
  <p class="disclaimer">{DISCLAIMER}</p>
</header>
{body_sections}
"""
    canonical = f"/pro/{pro_slug}/" if current else f"/pro/{pro_slug}/{week_key}.html"
    return shell(
        f"Weekly brief {week_key} — PolicyPulse Pro",
        "Unlisted PolicyPulse Pro weekly brief. Notices stay linked to the official source.",
        depth,
        "",
        body,
        canonical,
        robots="noindex, nofollow",
    )


def write_private_briefs(items: list[dict], pro_slug: str) -> str:
    groups = group_by_iso_week(items)
    current = current_iso_week()
    brief_dir = DOCS / "pro" / pro_slug
    brief_dir.mkdir(parents=True, exist_ok=True)
    monday, sunday = week_bounds(current)
    earlier = sorted(key for key in groups if key < current)
    (brief_dir / "index.html").write_text(
        page_brief(groups.get(current, []), current, monday, sunday, pro_slug, True, earlier),
        encoding="utf-8",
    )
    for key in earlier:
        start, end = week_bounds(key)
        (brief_dir / f"{key}.html").write_text(
            page_brief(groups[key], key, start, end, pro_slug, False),
            encoding="utf-8",
        )
    return current


def write_sitemap(paths: list[str]) -> str:
    lines = [
        '<?xml version="1.0" encoding="UTF-8"?>',
        '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">',
    ]
    for path in paths:
        loc = SITE + "/" if path in {"", "index.html"} else f"{SITE}/{path}"
        lines.append("<url>")
        lines.append(f"<loc>{esc(loc)}</loc>")
        lines.append("</url>")
    lines.append("</urlset>\n")
    return "\n".join(lines)


def main() -> int:
    items, manifest = load()
    if DOCS.exists():
        for child in DOCS.iterdir():
            if child.name == "config.js":
                continue
            if child.is_dir():
                shutil.rmtree(child)
            else:
                child.unlink()
    else:
        DOCS.mkdir(parents=True)
    (DOCS / "assets").mkdir(exist_ok=True)
    (DOCS / "sector").mkdir(exist_ok=True)
    (DOCS / "items").mkdir(exist_ok=True)
    shutil.copy(WEB / "assets" / "style.css", DOCS / "assets" / "style.css")
    shutil.copy(WEB / "assets" / "site.js", DOCS / "assets" / "site.js")
    favicon = WEB / "assets" / "favicon.svg"
    if favicon.exists():
        shutil.copy(favicon, DOCS / "assets" / "favicon.svg")
    config_path = DOCS / "config.js"
    if config_path.exists():
        existing_config = config_path.read_text(encoding="utf-8")
    elif (WEB / "config.js").exists():
        existing_config = (WEB / "config.js").read_text(encoding="utf-8")
    else:
        existing_config = ""
    pro_slug = load_pro_slug()
    config_text = render_config(existing_config, pro_slug)
    existing_paypal = _config_string(existing_config, "PAYPAL_CLIENT_ID")
    existing_plan = _config_string(existing_config, "PLAN_ID")
    if existing_paypal and _config_string(config_text, "PAYPAL_CLIENT_ID") != existing_paypal:
        raise SystemExit("refusing to rewrite config.js without the existing PayPal client id")
    if existing_plan and _config_string(config_text, "PLAN_ID") != existing_plan:
        raise SystemExit("refusing to rewrite config.js without the existing PayPal plan id")
    config_path.write_text(config_text, encoding="utf-8")
    (WEB / "config.js").write_text(config_text, encoding="utf-8")
    (DOCS / ".nojekyll").write_text("", encoding="utf-8")
    (DOCS / "robots.txt").write_text(robots_txt(pro_slug), encoding="utf-8")
    (DOCS / "index.html").write_text(page_home(items, manifest), encoding="utf-8")
    (DOCS / "about.html").write_text(page_about(), encoding="utf-8")
    (DOCS / "sources.html").write_text(page_sources(manifest), encoding="utf-8")
    (DOCS / "archive.html").write_text(page_archive(items), encoding="utf-8")
    (DOCS / "digest.html").write_text(page_digest(), encoding="utf-8")
    (DOCS / "pro.html").write_text(page_pro(), encoding="utf-8")
    paths = [
        "index.html",
        "about.html",
        "sources.html",
        "archive.html",
        "digest.html",
        "pro.html",
        "feed.xml",
    ]
    for slug, label in SECTORS:
        (DOCS / "sector" / f"{slug}.html").write_text(page_sector(slug, label, items), encoding="utf-8")
        paths.append(f"sector/{slug}.html")
    for item in items:
        (DOCS / "items" / f"{item['id']}.html").write_text(page_item(item), encoding="utf-8")
        paths.append(f"items/{item['id']}.html")
    (DOCS / "feed.xml").write_text(write_rss(items), encoding="utf-8")
    sitemap = write_sitemap(paths)
    if pro_slug in sitemap:
        raise SystemExit("refusing to publish the private brief path in sitemap.xml")
    (DOCS / "sitemap.xml").write_text(sitemap, encoding="utf-8")
    current_week = write_private_briefs(items, pro_slug)
    print(f"built {len(items)} item pages in {DOCS}")
    print(f"private brief week {current_week}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
