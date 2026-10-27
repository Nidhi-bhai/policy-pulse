"""Optional model brief. Used only when POLICYPULSE_LLM_API_KEY is set.

The site does not depend on this. Output is kept only when it does not
introduce a number that was absent from the source text.
"""

from __future__ import annotations

import json
import os
import re
from urllib.request import Request, urlopen

from .http import ssl_context
from .text import collapse

_NUMBER = re.compile(r"\d+(?:[.,]\d+)?%?|\u20b9\s*\d+")


def enabled() -> bool:
    return bool(os.environ.get("POLICYPULSE_LLM_API_KEY"))


def _numbers(text: str) -> set[str]:
    return set(_NUMBER.findall(text or ""))


def _grounded(model_text: str, source_text: str) -> bool:
    extra = _numbers(model_text) - _numbers(source_text)
    return not extra


def summarize(item: dict) -> str | None:
    key = os.environ.get("POLICYPULSE_LLM_API_KEY")
    if not key:
        return None
    source = collapse(f"{item.get('title', '')} {item.get('excerpt', '')}")
    if not source:
        return None
    base = os.environ.get("POLICYPULSE_LLM_BASE_URL", "https://api.openai.com/v1").rstrip("/")
    model = os.environ.get("POLICYPULSE_LLM_MODEL", "gpt-4o-mini")
    prompt = (
        "You write a three-sentence business brief for an Indian MSME reader. "
        "Use ONLY the source text below. Do not add rates, dates, penalties, or names "
        "that are not in the source. If the business effect is unclear, say so. "
        "Return plain text, no markdown.\n\nSource:\n" + source
    )
    payload = {
        "model": model,
        "temperature": 0,
        "messages": [
            {"role": "system", "content": "You never invent facts beyond the user-supplied source text."},
            {"role": "user", "content": prompt},
        ],
    }
    request = Request(
        f"{base}/chat/completions",
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {key}",
            "Content-Type": "application/json",
        },
        method="POST",
    )
    with urlopen(request, timeout=40, context=ssl_context()) as response:
        body = json.loads(response.read().decode("utf-8"))
    text = collapse(body["choices"][0]["message"]["content"])
    if not text or not _grounded(text, source):
        return None
    return text
