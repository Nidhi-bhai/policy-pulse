"""HTTP fetch with the system trust store plus bundled public CAs."""

from __future__ import annotations

import ssl
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[2]
CERT_DIR = ROOT / "certs"
# A normal browser agent. PIB and a few other public government pages
# answer 403 to non-browser agents. The archive still cites each source URL.
USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
)


def ssl_context() -> ssl.SSLContext:
    ctx = ssl.create_default_context()
    if CERT_DIR.is_dir():
        for pem in sorted(CERT_DIR.glob("*.pem")):
            ctx.load_verify_locations(str(pem))
    return ctx


def fetch(url: str, timeout: int = 45) -> tuple[str, bytes, str]:
    """Return (final_url, body, content_type). Raises URLError or HTTPError."""
    request = Request(
        url,
        headers={
            "User-Agent": USER_AGENT,
            "Accept": "application/rss+xml, application/xml, text/html, application/json;q=0.9, */*;q=0.8",
            "Accept-Language": "en-IN,en;q=0.9",
        },
    )
    context = ssl_context()
    try:
        with urlopen(request, timeout=timeout, context=context) as response:
            body = response.read()
            final = response.geturl()
            ctype = response.headers.get("Content-Type", "")
            return final, body, ctype
    except (HTTPError, URLError, TimeoutError):
        raise


def fetch_text(url: str, timeout: int = 45) -> str:
    _final, body, ctype = fetch(url, timeout=timeout)
    charset = "utf-8"
    if "charset=" in ctype.lower():
        charset = ctype.lower().split("charset=")[-1].split(";")[0].strip() or "utf-8"
    if body.startswith(b"\xef\xbb\xbf"):
        body = body[3:]
    try:
        return body.decode(charset, errors="replace")
    except LookupError:
        return body.decode("utf-8", errors="replace")
