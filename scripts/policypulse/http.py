"""HTTP fetch with the system trust store plus bundled public CAs."""

from __future__ import annotations

import ssl
import time
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[2]
CERT_DIR = ROOT / "certs"
# A normal browser agent. PIB, DGFT, and a few other public government pages
# answer 403 to non-browser agents. The archive still cites each source URL.
USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"
)
# Status codes that are often transient or bot-walls. A later attempt, or
# another endpoint, can still succeed. 404 is a real miss and is not retried.
RETRY_STATUS = {403, 408, 429, 500, 502, 503, 504}


def ssl_context() -> ssl.SSLContext:
    ctx = ssl.create_default_context()
    if CERT_DIR.is_dir():
        for pem in sorted(CERT_DIR.glob("*.pem")):
            ctx.load_verify_locations(str(pem))
    return ctx


def browser_headers(referer: str | None = None) -> dict[str, str]:
    headers = {
        "User-Agent": USER_AGENT,
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,application/rss+xml;q=0.8,*/*;q=0.7",
        "Accept-Language": "en-IN,en;q=0.9",
        "Cache-Control": "no-cache",
        "Pragma": "no-cache",
        "sec-ch-ua": '"Google Chrome";v="131", "Chromium";v="131", "Not_A Brand";v="24"',
        "sec-ch-ua-mobile": "?0",
        "sec-ch-ua-platform": '"Windows"',
        "Sec-Fetch-Dest": "document",
        "Sec-Fetch-Mode": "navigate",
        "Sec-Fetch-User": "?1",
        "Upgrade-Insecure-Requests": "1",
    }
    if referer:
        headers["Referer"] = referer
        headers["Sec-Fetch-Site"] = "same-origin"
    else:
        headers["Sec-Fetch-Site"] = "none"
    return headers


def should_retry(exc: BaseException, attempt: int, retries: int) -> bool:
    """True when another attempt is allowed for this failure."""
    if attempt >= retries:
        return False
    if isinstance(exc, HTTPError):
        return exc.code in RETRY_STATUS
    return isinstance(exc, (URLError, TimeoutError))


def fetch(
    url: str,
    timeout: int = 45,
    referer: str | None = None,
    retries: int = 2,
) -> tuple[str, bytes, str]:
    """Return (final_url, body, content_type). Raises URLError or HTTPError."""
    context = ssl_context()
    last: BaseException | None = None
    for attempt in range(retries + 1):
        request = Request(url, headers=browser_headers(referer))
        try:
            with urlopen(request, timeout=timeout, context=context) as response:
                body = response.read()
                final = response.geturl()
                ctype = response.headers.get("Content-Type", "")
                return final, body, ctype
        except HTTPError as exc:
            last = exc
            try:
                exc.close()
            except Exception:
                pass
            if not should_retry(exc, attempt, retries):
                raise
            time.sleep(1.5 * (attempt + 1))
        except (URLError, TimeoutError) as exc:
            last = exc
            if not should_retry(exc, attempt, retries):
                raise
            time.sleep(1.5 * (attempt + 1))
    if last is not None:
        raise last
    raise URLError(f"fetch failed for {url}")


def fetch_text(
    url: str,
    timeout: int = 45,
    referer: str | None = None,
    retries: int = 2,
) -> str:
    _final, body, ctype = fetch(url, timeout=timeout, referer=referer, retries=retries)
    charset = "utf-8"
    if "charset=" in ctype.lower():
        charset = ctype.lower().split("charset=")[-1].split(";")[0].strip() or "utf-8"
    if body.startswith(b"\xef\xbb\xbf"):
        body = body[3:]
    try:
        return body.decode(charset, errors="replace")
    except LookupError:
        return body.decode("utf-8", errors="replace")
