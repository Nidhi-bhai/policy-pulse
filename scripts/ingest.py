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


def source_counts(items: list[dict]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for item in items:
        source = item.get("source") or ""
        counts[source] = counts.get(source, 0) + 1
    return counts


def failed_sources_shrunk(before: dict[str, int], after: dict[str, int], report: list[dict]) -> list[str]:
    """Sources that failed this run and would leave the archive with fewer rows."""
    shrunk = []
    for row in report:
        if row.get("ok"):
            continue
        source_id = row.get("id") or ""
        if after.get(source_id, 0) < before.get(source_id, 0):
            shrunk.append(source_id)
    return shrunk


def retag(items: list[dict]) -> list[dict]:
    """Recompute sector tags from stored titles so rule fixes apply without a refetch."""
    return [annotate(dict(item)) for item in items]


def main() -> int:
    existing = load_items()
    before = source_counts(existing)
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
            if source_id == "dgft":
                print(
                    f"DGFT fetch failed; keeping {before.get('dgft', 0)} existing items",
                    file=sys.stderr,
                )
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

    merged = retag(merge_all(existing, fresh))
    after = source_counts(merged)
    shrunk = failed_sources_shrunk(before, after, report)
    if shrunk:
        print(
            "refusing to save; a failed fetch would drop archived items: " + ", ".join(shrunk),
            file=sys.stderr,
        )
        return 1
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
