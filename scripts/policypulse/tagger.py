"""Keyword sector tags and briefs built only from source text.

The brief quotes the official title (and a short excerpt when it is prose).
Impact lines fire only when a trigger word is actually present. They do not
state rates, deadlines, or legal effects that the source text did not give us.
"""

from __future__ import annotations

import re

from .text import collapse, excerpt, has_devanagari, mostly_numeric

SECTORS: list[tuple[str, str]] = [
    ("exports", "Exports & trade"),
    ("agri", "Agriculture"),
    ("msme", "MSME"),
    ("banking", "Banking & finance"),
    ("gst", "GST & indirect tax"),
    ("pharma", "Pharma & health"),
    ("startups", "Startups"),
]

SECTOR_LABEL = dict(SECTORS)

# "Shubhang Exports Ltd" is a company in a SEBI order, not the exports sector.
# Strip that phrase before the exports patterns run. "export policy" and
# "merchandise exports" do not have a company suffix, so they still match.
_EXPORT_COMPANY = re.compile(
    r"\bexports?\s+(?:pvt\.?|private|ltd\.?|limited|llp|inc\.?|corp\.?|corporation|co\.?)\b",
    flags=re.I,
)

# Patterns are matched against the official title plus a short excerpt.
_SECTOR_PATTERNS: dict[str, list[str]] = {
    "exports": [
        r"\bexports?\b",
        r"\bimporters?\b",
        r"\bimports?\b",
        r"\bdgft\b",
        r"foreign trade",
        r"trade notice",
        r"\brodtep\b",
        r"\bdrawback\b",
        r"shipping bill",
        r"\bicegate\b",
        r"\bsez\b",
        r"\bepcg\b",
        r"itc\s*\(hs\)",
        r"\bhs code\b",
        r"exim",
        r"customs duty",
        r"\bfta\b",
        r"merchandise exports",
        r"निर्यात",
        r"आयात",
    ],
    "agri": [
        r"agricultur",
        r"\bfarmers?\b",
        r"\bcrops?\b",
        r"\bkharif\b",
        r"\brabi\b",
        r"fertili[sz]er",
        r"\bapmc\b",
        r"\bmandi\b",
        r"foodgrain",
        r"\brice\b",
        r"\bwheat\b",
        r"\bsugar\b",
        r"\bpulses?\b",
        r"\bonion\b",
        r"\bdairy\b",
        r"\bfisher",
        r"\blivestock\b",
        r"\bmsp\b",
        r"\bpds\b",
        r"कृषि",
        r"किसान",
    ],
    "msme": [
        r"\bmsmes?\b",
        r"micro,? small",
        r"small enterprise",
        r"\budyam\b",
        r"\bmudra\b",
        r"\bcgtmse\b",
        r"delayed payment",
        r"\bsidbi\b",
        r"\bkhadi\b",
        r"small business",
        r"cottage industr",
    ],
    "banking": [
        r"\brbi\b",
        r"\bbanks?\b",
        r"\bnbfc",
        r"\brepo\b",
        r"\bcrr\b",
        r"\bslr\b",
        r"\bfema\b",
        r"\bloans?\b",
        r"\bcredit\b",
        r"\bdeposits?\b",
        r"\bkyc\b",
        r"\bupi\b",
        r"monetary policy",
        r"co-?operative bank",
        r"priority sector",
        r"\bpsl\b",
        r"liquidity",
        r"treasury bill",
        r"government securit",
    ],
    "gst": [
        r"\bgst\b",
        r"\bcgst\b",
        r"\bigst\b",
        r"\bsgst\b",
        r"\butgst\b",
        r"\bgstr\b",
        r"input tax",
        r"e-?way",
        r"\bcbic\b",
        r"indirect tax",
        r"\bhsn\b",
        r"central tax",
        r"compensation cess",
    ],
    "pharma": [
        r"\bpharma",
        r"\bdrugs?\b",
        r"\bmedicines?\b",
        r"\bcdsco\b",
        r"\bnppa\b",
        r"medical device",
        r"\bvaccines?\b",
        r"clinical trial",
        r"bulk drug",
        r"active pharmaceutical",
        r"\bwho-gmp\b",
    ],
    "startups": [
        r"\bstart-?ups?\b",
        r"\bdpiit\b",
        r"angel tax",
        r"\besops?\b",
        r"fund of funds",
        r"\bincubator",
        r"seed fund",
        r"startup india",
    ],
}

# (pattern, sentence). The sentence may only describe the words that matched.
_IMPACT_RULES: list[tuple[str, str]] = [
    (
        r"\b(prohibit|restricted|restriction|banned|ban on)\b",
        "The official text uses restriction or prohibition language. Anyone who ships, stocks, or prices the goods or services named in the headline should read the source before the next contract.",
    ),
    (
        r"\b(amend(?:ed|ment|s)?|revised|revision|substitut)\b",
        "The official text says an existing instruction is amended or revised. Check the source for whether a form, condition, or list you already follow has changed.",
    ),
    (
        r"\b(extend(?:ed|sion)?|deadline|due date|last date|timeline)\b",
        "The official text refers to a timeline. Read the source for the date before you rely on it. PolicyPulse does not restate a deadline that is not in the headline.",
    ),
    (
        r"\b(repo|crr|slr|bank rate|liquidity adjustment|monetary policy)\b",
        "The official text is about a banking or money-market instrument. Treasury and credit teams should read the source for the operative line.",
    ),
    (
        r"\b(duty|tariff|drawback|rodtep|rate of)\b",
        "The official text mentions a duty, tariff, or incentive. The rate, if any, is only in the source document. Do not take a number from this brief.",
    ),
    (
        r"\b(registration|licence|license|authorisation|authorization|compliance)\b",
        "The official text mentions a registration, licence, or compliance step. Open the source to see who it applies to.",
    ),
]


def tag_sectors(text: str) -> list[str]:
    found: list[str] = []
    haystack = text or ""
    exports_haystack = _EXPORT_COMPANY.sub(" ", haystack)
    for slug, _label in SECTORS:
        probe = exports_haystack if slug == "exports" else haystack
        for pattern in _SECTOR_PATTERNS[slug]:
            if re.search(pattern, probe, flags=re.I):
                found.append(slug)
                break
    return found


def _impact_sentences(text: str) -> list[str]:
    lines: list[str] = []
    for pattern, sentence in _IMPACT_RULES:
        if re.search(pattern, text, flags=re.I):
            lines.append(sentence)
    if not lines:
        lines.append(
            "The business effect cannot be read off the headline alone. Open the source before you change a price, a filing, or a shipment."
        )
    return lines


def annotate(item: dict) -> dict:
    """Fill brief fields. Does not invent figures or dates."""
    title = collapse(item.get("title") or "")
    source_excerpt = item.get("excerpt") or ""
    digit_count = sum(ch.isdigit() for ch in source_excerpt)
    if mostly_numeric(source_excerpt) or ("crore" in source_excerpt.lower() and digit_count > 12):
        source_excerpt = ""
    else:
        source_excerpt = excerpt(source_excerpt, 280)
    basis_text = collapse(f"{title} {source_excerpt}")
    sectors = tag_sectors(basis_text)

    instrument = collapse(item.get("instrument") or "")
    body = collapse(item.get("body_name") or "")
    lead_bits = []
    if instrument:
        lead_bits.append(instrument)
    if body and body.lower() not in title.lower():
        lead_bits.append(body)
    lead = ""
    if lead_bits:
        lead = "Listed by the source as " + ", ".join(lead_bits) + ". "

    what = f"{lead}Official headline: “{title}”."
    if source_excerpt and source_excerpt.lower() not in title.lower():
        what += f" Source text includes: “{source_excerpt}”."
    if has_devanagari(title) and not re.search(r"[A-Za-z]{3,}", title):
        what += " This headline is in Hindi on the official feed. The English wording above is the headline itself, not a translation."

    if sectors:
        labels = ", ".join(SECTOR_LABEL[slug] for slug in sectors)
        who = (
            f"Sector tags come only from words in that text: {labels}. "
            "A tag means the word appeared. It does not mean every firm in that sector is covered."
        )
    else:
        who = (
            "No sector keyword from the PolicyPulse list matched this text, "
            "so the item stays on the latest feed and is not filed on a sector page."
        )

    impact_lines = _impact_sentences(basis_text)
    impact = " ".join(impact_lines)
    action = (
        "Open the official source linked on this page and check whether it changes anything you file, ship, price, or lend. "
        "This brief is a reading aid, not legal, tax, or investment advice."
    )

    item = dict(item)
    item["sectors"] = sectors
    item["what_changed"] = what
    item["who_affected"] = who
    item["impact"] = impact
    item["action"] = action
    item["basis"] = "keyword-rules"
    item["excerpt"] = source_excerpt
    return item
