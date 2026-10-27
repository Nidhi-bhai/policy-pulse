#!/usr/bin/env python3
"""Pull official public feeds and merge them into the growing archive."""

from __future__ import annotations

import os
import sys
import traceback
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from policypulse.archive import load_items, merge_all, save_archive  # noqa: E402
from policypulse.llm import enabled as llm_enabled  # noqa: E402
from policypulse.llm import summarize  # noqa: E402
from policypulse.sources import FETCHERS  # noqa: E402
from policypulse.tagger import annotate  # noqa: E402
from policypulse.text import now_ist  # noqa: E402


def main() -> int:
    existing = load_items()
    known = {item["id"] for item in existing}
    fresh: list[dict] = []
    report = []
    for source_id, name, url, fetcher in FETCHERS:
        try:
            rows = [annotate(row) for row in fetcher()]
            fresh.extend(rows)
            report.append(
                {
                    "id": source_id,
                    "name": name,
                    "url": url,
                    "ok": True,
                    "fetched": len(rows),
                    "error": None,
                }
            )
            print(f"ok  {source_id:10} {len(rows):4} items")
        except Exception as exc:  # one source must not sink the run
            report.append(
                {
                    "id": source_id,
                    "name": name,
                    "url": url,
                    "ok": False,
                    "fetched": 0,
                    "error": f"{type(exc).__name__}: {exc}",
                }
            )
            print(f"ERR {source_id:10} {exc}", file=sys.stderr)
            traceback.print_exc()

    if llm_enabled():
        budget = int(os.environ.get("POLICYPULSE_LLM_MAX", "20"))
        used = 0
        for row in fresh:
            if used >= budget:
                break
            if row["id"] in known and any(
                old.get("id") == row["id"] and old.get("llm_summary") for old in existing
            ):
                continue
            try:
                note = summarize(row)
            except Exception as exc:
                print(f"llm skip {row['id']}: {exc}", file=sys.stderr)
                continue
            if note:
                row["llm_summary"] = note
                row["llm_basis"] = "optional-model-grounded"
                used += 1
        print(f"llm notes kept: {used}")
    else:
        print("llm skipped (POLICYPULSE_LLM_API_KEY not set)")

    stamped = now_ist()
    for row in fresh:
        row["fetched_at"] = stamped

    merged = merge_all(existing, fresh)
    families = {row["source"] for row in merged}
    ok_families = {row["id"] for row in report if row["ok"] and row["fetched"] > 0}
    manifest = {
        "generated_at": stamped,
        "item_count": len(merged),
        "source_families": sorted(families),
        "sources_ok": sorted(ok_families),
        "llm": "on" if llm_enabled() else "off",
        "sources": report,
    }
    save_archive(merged, manifest)
    print(f"archive {len(merged)} items across {len(families)} sources")
    if len(merged) < 50 or len(families) < 3:
        print("archive is below the 50-item / 3-source bar", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
