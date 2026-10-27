#!/usr/bin/env python3
"""Build the static PolicyPulse site from data/items.json into docs/."""

from __future__ import annotations

import html
import json
import shutil
import sys
from email.utils import format_datetime
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from policypulse.tagger import SECTORS, SECTOR_LABEL  # noqa: E402
from policypulse.text import format_display_date  # noqa: E402

SITE = "https://nidhi-bhai.github.io/policy-pulse"
DOCS = ROOT / "docs"
WEB = ROOT / "web"
DATA = ROOT / "data" / "items.json"
MANIFEST = ROOT / "data" / "manifest.json"
IST = ZoneInfo("Asia/Kolkata")

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


def chips(item: dict, depth: int) -> str:
    parts = []
    for slug in item.get("sectors") or []:
        label = SECTOR_LABEL.get(slug, slug)
        parts.append(
            f'<a class="chip {esc(slug)}" href="{esc(rel(depth, f"sector/{slug}.html"))}">{esc(label)}</a>'
        )
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


def shell(title: str, description: str, depth: int, current: str, body: str, canonical_path: str) -> str:
    pre = prefix(depth)
    nav = []
    for path, label in NAV:
        current_attr = ' aria-current="page"' if path == current else ""
        nav.append(f'<a href="{esc(rel(depth, path))}"{current_attr}>{esc(label)}</a>')
    canonical = SITE + canonical_path
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{esc(title)}</title>
  <meta name="description" content="{esc(description)}">
  <link rel="canonical" href="{esc(canonical)}">
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
    <p class="lede">PolicyPulse turns public Indian government notices into a short business brief for MSMEs, traders, exporters, and investors. Every card links the official source. The wording is taken from that source, not from a guess.</p>
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
  <p class="lede">{len(items)} notices kept with their source URL and date. Daily runs add items. They do not delete old ones. Month files live in the repository under <code>data/archive/</code>.</p>
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
  <p class="lede">A static site cannot send mail on its own. Use this form as a mailto placeholder, or set <code>DIGEST_FORM_ACTION</code> in <code>config.js</code> to a Google Form or other static form endpoint.</p>
</header>
<form id="digest-form" class="panel" method="post" action="mailto:you@example.com" enctype="text/plain">
  <p id="digest-mode" class="note">Placeholder mode: submitting opens a mail draft to the address in config.js. Replace <code>DIGEST_MAILTO</code> before you share the page.</p>
  <label for="email">Email</label>
  <input id="email" name="email" type="email" required autocomplete="email" placeholder="you@company.com">
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
    body = """
<header class="page-head">
  <p class="eyebrow">Pro · $9/month</p>
  <h1>Weekly sector brief.</h1>
  <p class="lede">Pro is a PayPal subscription for a weekly sector brief. The button reads <code>PAYPAL_CLIENT_ID</code> and <code>PLAN_ID</code> from <code>config.js</code>. Card numbers never touch this repository.</p>
</header>
<section class="panel">
  <h2>What you are paying for</h2>
  <p>A weekly pass across the seven sector pages: exports, agriculture, MSME, banking, GST, pharma, and startups. The underlying notices stay free on this site. The subscription is how the brief is funded.</p>
  <p>Create a $9/month plan in PayPal, then paste the client id and plan id into <code>config.js</code>. Until those values are set, checkout stays off on purpose.</p>
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
    if not (DOCS / "config.js").exists():
        shutil.copy(WEB / "config.js", DOCS / "config.js")
    (DOCS / ".nojekyll").write_text("", encoding="utf-8")
    (DOCS / "robots.txt").write_text(
        "User-agent: *\nAllow: /\nSitemap: " + SITE + "/sitemap.xml\n",
        encoding="utf-8",
    )
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
    (DOCS / "sitemap.xml").write_text(write_sitemap(paths), encoding="utf-8")
    print(f"built {len(items)} item pages in {DOCS}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
