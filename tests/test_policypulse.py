"""Unit tests for the brief, archive merge, and parsers. No network."""

from __future__ import annotations

import sys
import unittest
from datetime import date
from pathlib import Path
from unittest.mock import patch
from urllib.error import HTTPError, URLError

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from policypulse.archive import merge_all  # noqa: E402
from policypulse.http import fetch, should_retry  # noqa: E402
from policypulse.sources import (  # noqa: E402
    _RowParser,
    _pib_links,
    _sebi_circular_rows,
    dgft_candidate_urls,
    dgft_listing_ok,
)
from policypulse.tagger import annotate  # noqa: E402
from policypulse.text import parse_date, stable_id  # noqa: E402

import build_site  # noqa: E402
import ingest  # noqa: E402


class DateTests(unittest.TestCase):
    def test_indian_numeric_and_month_names(self):
        self.assertEqual(parse_date("26/10/2026"), "2026-10-26")
        self.assertEqual(parse_date("27-Oct-2026"), "2026-10-27")
        self.assertEqual(parse_date("Oct 23, 2026"), "2026-10-23")
        self.assertEqual(parse_date("Tue, 27 Oct 2026 09:00:00"), "2026-10-27")
        self.assertEqual(parse_date("11th July 2026"), "2026-07-11")
        self.assertEqual(parse_date("24.06.2026"), "2026-06-24")
        self.assertIsNone(parse_date("no date here"))


class TaggerTests(unittest.TestCase):
    def test_quotes_title_and_does_not_invent_a_rate(self):
        item = annotate(
            {
                "title": "Amendment in import policy of raw sugar",
                "excerpt": "DGFT notification on the import policy of raw sugar.",
                "instrument": "DGFT notification 45 (2026)",
                "body_name": "DGFT",
            }
        )
        self.assertIn("raw sugar", item["what_changed"])
        self.assertIn("exports", item["sectors"])
        self.assertNotIn("%", item["impact"])
        self.assertNotIn("₹", item["what_changed"])
        self.assertIn("amended", item["impact"].lower())

    def test_timeline_sentence_only_when_the_word_is_present(self):
        plain = annotate({"title": "Minutes of the committee meeting", "excerpt": ""})
        timed = annotate({"title": "Extension of the filing deadline", "excerpt": ""})
        self.assertNotIn("timeline", plain["impact"].lower())
        self.assertIn("timeline", timed["impact"].lower())

    def test_no_sector_when_nothing_matches(self):
        item = annotate({"title": "Floral tributes on a birth anniversary", "excerpt": ""})
        self.assertEqual(item["sectors"], [])
        self.assertIn("not filed", item["who_affected"])

    def test_company_named_exports_ltd_is_not_the_exports_sector(self):
        item = annotate(
            {
                "title": (
                    "Completion of Recovery Certificate No. 6665 of 2023 issued to "
                    "Shubhang Exports Ltd. [Defaulter] in the matter of Sulabh Engineers"
                ),
                "excerpt": "",
            }
        )
        self.assertNotIn("exports", item["sectors"])

    def test_export_policy_still_counts_beside_a_company_name(self):
        item = annotate(
            {
                "title": "Shubhang Exports Ltd and the amendment of the export policy of raw sugar",
                "excerpt": "",
            }
        )
        self.assertIn("exports", item["sectors"])

    def test_pharma_inside_a_company_name_is_not_the_pharma_sector(self):
        item = annotate(
            {
                "title": (
                    "SEBI Order for Compliance dated 26.10.2026 issued against "
                    "Add Life Pharma Ltd in the matter of Add Life Pharma Ltd"
                ),
                "excerpt": "",
            }
        )
        self.assertNotIn("pharma", item["sectors"])
        self.assertTrue(item["impact_from_notice"])
        self.assertIn("compliance", item["impact"].lower())

    def test_bank_ltd_does_not_tag_banking_unless_the_notice_says_so(self):
        party = annotate({"title": "Recovery order issued against Yes Bank Ltd", "excerpt": ""})
        self.assertNotIn("banking", party["sectors"])
        stated = annotate({"title": "Yes Bank Ltd and the revised repo rate", "excerpt": ""})
        self.assertIn("banking", stated["sectors"])

    def test_exporters_outside_a_company_name_still_count(self):
        item = annotate({"title": "Public notice issued to all exporters of rice", "excerpt": ""})
        self.assertIn("exports", item["sectors"])
        self.assertIn("agri", item["sectors"])

    def test_impact_note_is_absent_when_the_notice_states_none(self):
        item = annotate({"title": "Minutes of the committee meeting", "excerpt": ""})
        self.assertEqual(item["impact"], "")
        self.assertFalse(item["impact_from_notice"])


class ArchiveTests(unittest.TestCase):
    def test_merge_keeps_old_items_and_prefers_english_title(self):
        old = [
            {
                "id": "keep-me",
                "title": "Older notice",
                "url": "https://example.test/old",
                "first_seen": "2026-01-01T00:00:00+05:30",
                "date": "2026-01-01",
            }
        ]
        fresh = [
            {
                "id": "pib-1",
                "title": "अंग्रेजी शीर्षक नहीं",
                "url": "https://pib.gov.in/x",
                "fetched_at": "2026-10-27T10:00:00+05:30",
            },
            {
                "id": "pib-1",
                "title": "English headline about exports",
                "url": "https://pib.gov.in/x",
                "fetched_at": "2026-10-27T10:00:00+05:30",
                "date": "2026-10-27",
            },
        ]
        merged = merge_all(old, fresh)
        ids = {row["id"] for row in merged}
        self.assertIn("keep-me", ids)
        self.assertIn("pib-1", ids)
        current = next(row for row in merged if row["id"] == "pib-1")
        self.assertEqual(current["title"], "English headline about exports")
        self.assertEqual(current["first_seen"], "2026-10-27T10:00:00+05:30")
        kept = next(row for row in merged if row["id"] == "keep-me")
        self.assertEqual(kept["first_seen"], "2026-01-01T00:00:00+05:30")


class ParserTests(unittest.TestCase):
    def test_dgft_row(self):
        html = """
        <table><tbody>
        <tr>
          <td>1</td>
          <td>32</td>
          <td>2026-27</td>
          <td>Amendments to the guidelines for export promotion</td>
          <td>26/10/2026</td>
          <td>26/10/2026 10:55:46</td>
          <td><a href="https://content.dgft.gov.in/Website/dgftprod/abc/notice.pdf">Download</a></td>
        </tr>
        </tbody></table>
        """
        parser = _RowParser()
        parser.feed(html)
        self.assertEqual(len(parser.rows), 1)
        self.assertIn("export promotion", parser.rows[0]["cells"][3])
        self.assertIn("content.dgft.gov.in", parser.rows[0]["href"])

    def test_pib_and_sebi_snippets(self):
        pib = """
        <ul><li><h3 class='font104'>Ministry of Commerce & Industry</h3>
        <ul class='num'><li><a title='DPIIT note' href='/PressReleaseDetail.aspx?PRID=2328842'>DPIIT startup support</a></li></ul></li></ul>
        """
        self.assertEqual(_pib_links(pib)[0][1], "2328842")
        sebi = """
        <tr role='row' class='odd'>
          <td>Oct 23, 2026</td>
          <td><a href="https://www.sebi.gov.in/legal/circulars/oct-2026/example_1.html">Review of call records</a>
        </tr>
        """
        rows = _sebi_circular_rows(sebi)
        self.assertEqual(rows[0][2], "Review of call records")
        self.assertEqual(parse_date(rows[0][0]), "2026-10-23")

    def test_ids_are_stable(self):
        self.assertEqual(stable_id("dgft", "https://example.test/a"), stable_id("dgft", "https://example.test/a"))


class DgftResilienceTests(unittest.TestCase):
    def test_fallback_urls_cover_www_index_and_apex(self):
        urls = dgft_candidate_urls("trade-notice")
        self.assertEqual(urls[0], "https://www.dgft.gov.in/CP/?opt=trade-notice")
        self.assertIn("index.jsp?opt=trade-notice", urls[1])
        self.assertEqual(urls[2], "https://dgft.gov.in/CP/?opt=trade-notice")

    def test_block_page_is_not_a_listing(self):
        self.assertFalse(dgft_listing_ok("<html><title>Access Denied</title></html>"))
        self.assertFalse(dgft_listing_ok("<table id='metaTable'></table>"))
        listing = "<table id='metaTable'><a href='https://content.dgft.gov.in/Website/x.pdf'>pdf</a></table>"
        self.assertTrue(dgft_listing_ok(listing))

    def test_403_is_retried_and_404_is_not(self):
        forbidden = HTTPError("https://www.dgft.gov.in/", 403, "Forbidden", hdrs=None, fp=None)
        missing = HTTPError("https://www.dgft.gov.in/", 404, "Not Found", hdrs=None, fp=None)
        self.assertTrue(should_retry(forbidden, 0, 2))
        self.assertFalse(should_retry(forbidden, 2, 2))
        self.assertFalse(should_retry(missing, 0, 2))
        self.assertTrue(should_retry(URLError("timed out"), 0, 2))

    def test_fetch_retries_403_then_returns_body(self):
        calls = {"n": 0}

        class Response:
            headers = {"Content-Type": "text/html; charset=utf-8"}

            def read(self):
                return b"ok"

            def geturl(self):
                return "https://www.dgft.gov.in/final"

            def __enter__(self):
                return self

            def __exit__(self, *args):
                return False

        def fake_urlopen(request, timeout=45, context=None):
            calls["n"] += 1
            if calls["n"] == 1:
                raise HTTPError(request.full_url, 403, "Forbidden", hdrs=None, fp=None)
            return Response()

        with patch("policypulse.http.urlopen", fake_urlopen), patch("policypulse.http.time.sleep"):
            final, body, _ctype = fetch("https://www.dgft.gov.in/CP/?opt=trade-notice", retries=2)
        self.assertEqual(calls["n"], 2)
        self.assertEqual(body, b"ok")
        self.assertIn("dgft.gov.in", final)

    def test_fetch_uses_curl_after_a_final_403(self):
        def fake_urlopen(request, timeout=45, context=None):
            raise HTTPError(request.full_url, 403, "Forbidden", hdrs=None, fp=None)

        class Completed:
            returncode = 0
            stdout = b"<table id='metaTable'>https://content.dgft.gov.in/x.pdf</table>\n200 https://www.dgft.gov.in/final"
            stderr = b""

        with patch("policypulse.http.urlopen", fake_urlopen), patch("policypulse.http.time.sleep"), patch(
            "policypulse.http.shutil.which", return_value="/usr/bin/curl"
        ), patch("policypulse.http.subprocess.run", return_value=Completed()):
            final, body, _ctype = fetch("https://www.dgft.gov.in/CP/?opt=trade-notice", retries=0)
        self.assertEqual(final, "https://www.dgft.gov.in/final")
        self.assertIn(b"content.dgft.gov.in", body)


class IngestGuardTests(unittest.TestCase):
    def test_failed_dgft_must_not_shrink_the_archive(self):
        before = {"dgft": 512, "pib": 31}
        after = {"dgft": 512, "pib": 31}
        report = [{"id": "dgft", "ok": False, "fetched": 0}, {"id": "pib", "ok": True, "fetched": 2}]
        self.assertEqual(ingest.failed_sources_shrunk(before, after, report), [])
        after["dgft"] = 0
        self.assertEqual(ingest.failed_sources_shrunk(before, after, report), ["dgft"])


class SiteCopyTests(unittest.TestCase):
    def test_digest_uses_the_real_mailbox(self):
        html = build_site.page_digest()
        self.assertIn("mailto:nidhi69n@gmail.com?subject=PolicyPulse%20digest", html)
        self.assertNotIn("example.com", html)

    def test_home_and_pro_state_delivery_and_the_disclaimer(self):
        home = build_site.page_home([], {"source_families": ["pib", "rbi", "dgft"], "generated_at": "2026-10-27T10:00:00+05:30"})
        pro = build_site.page_pro()
        for page in (home, pro):
            self.assertIn("PolicyPulse is not a government site. Verify every notice on the official source.", page)
            self.assertIn("weekly brief", page)
            self.assertNotIn("example.com", page)
        self.assertIn("updates daily", home)
        self.assertIn("2023–26 backfill", home)
        self.assertIn("a link to the unlisted weekly Pro brief page, updated every Monday; no renewal, no account", pro)
        self.assertIn("sector-sorted weekly list with official links and an impact note where the notice states one", pro)
        self.assertIn("Lost your link? Email nidhi69n@gmail.com with your PayPal order id.", pro)
        self.assertIn("Not legal, tax or investment advice.", home)
        self.assertIn("Not legal, tax or investment advice.", pro)
        self.assertNotIn("pro-email", pro)
        self.assertNotIn("subscription", pro.lower())
        self.assertNotIn("PLAN_ID", pro)
        self.assertNotIn("form URL", pro)
        self.assertNotIn("Add <code>PAYPAL_CLIENT_ID</code>", pro)
        self.assertNotIn("private", pro.lower())
        self.assertNotIn("e31e1b36d2727e090f84fe9c60ab2c15", pro)

    def test_backfill_chip_uses_the_source_date(self):
        old = {
            "id": "old",
            "title": "Notification on import of pulses",
            "source": "dgft",
            "source_name": "DGFT",
            "date": "2024-05-01",
            "sectors": ["agri"],
            "what_changed": "Official headline.",
            "url": "https://content.dgft.gov.in/old.pdf",
        }
        fresh = dict(old, id="fresh", date="2026-10-26")
        undated = dict(old, id="none", date=None)
        old_html = build_site.card(old, 0)
        self.assertIn("01 May 2024", old_html)
        self.assertIn("Backfill", old_html)
        self.assertNotIn("Backfill", build_site.card(fresh, 0))
        undated_html = build_site.card(undated, 0)
        self.assertIn("Date not in source", undated_html)
        self.assertNotIn("Backfill", undated_html)

    def test_sources_page_shows_the_recorded_fetch(self):
        html = build_site.page_sources(
            {
                "generated_at": "2026-10-27T13:46:07+05:30",
                "sources": [
                    {"name": "DGFT", "ok": False, "fetched": 0, "error": "HTTP Error 403: Forbidden"},
                    {"name": "PIB", "ok": True, "fetched": 31, "error": None},
                ],
            }
        )
        self.assertIn("2026-10-27T13:46:07+05:30", html)
        self.assertIn("Failed", html)
        self.assertIn("HTTP Error 403: Forbidden", html)
        self.assertIn("Fetched", html)

    def test_unlisted_brief_is_noindex_and_omits_undated_items(self):
        items = [
            {
                "id": "gst-1",
                "date": "2026-10-26",
                "title": "GST ticker",
                "sectors": ["gst"],
                "impact": "The official text says an existing instruction is amended or revised.",
                "impact_from_notice": True,
                "url": "https://cbic-gst.gov.in/tickers.html",
                "source_name": "CBIC / GST",
            },
            {
                "id": "plain",
                "date": "2026-10-27",
                "title": "Committee minutes",
                "sectors": [],
                "impact": "The business effect cannot be read off the headline alone.",
                "impact_from_notice": False,
                "url": "https://pib.gov.in/minutes",
                "source_name": "PIB",
            },
            {
                "id": "nodate",
                "date": None,
                "title": "Undated Hindi headline",
                "sectors": ["gst"],
                "impact": "Should not be filed into a week.",
                "url": "https://pib.gov.in/x",
                "source_name": "PIB",
            },
        ]
        groups = build_site.group_by_iso_week(items)
        self.assertEqual(list(groups), ["2026-W44"])
        self.assertEqual([row["id"] for row in groups["2026-W44"]], ["plain", "gst-1"])
        monday, sunday = build_site.week_bounds("2026-W44")
        self.assertEqual(monday, date(2026, 10, 26))
        self.assertEqual(sunday, date(2026, 11, 1))
        page = build_site.page_brief(groups["2026-W44"], "2026-W44", monday, sunday, "a" * 32, True)
        self.assertIn("noindex, nofollow", page)
        self.assertIn("GST ticker", page)
        self.assertIn("amended or revised", page)
        self.assertNotIn("cannot be read off the headline", page)
        self.assertNotIn("Undated Hindi headline", page)
        self.assertIn("sector-sorted weekly list with official links and an impact note where the notice states one", page)
        self.assertNotIn("private", page.lower())
        robots = build_site.robots_txt("a" * 32)
        self.assertIn("Disallow: /policy-pulse/pro/" + ("a" * 32) + "/", robots)
        self.assertIn("Disallow: /pro/" + ("a" * 32) + "/", robots)
        sitemap = build_site.write_sitemap(["index.html", "pro.html", "items/gst-1.html"])
        self.assertNotIn("a" * 32, sitemap)
        self.assertNotIn("/pro/", sitemap)

    def test_config_keeps_paypal_and_drops_the_example_mailbox(self):
        existing = """
        window.POLICY_PULSE_CONFIG = {
          PAYPAL_CLIENT_ID: "BAAb5cq2I0Xx3lFhRJNBjnuGCVT5VDtWfWHgAuSasCoaA_F4cFzLmDWcDmYhsXG6panQVSaRPR3gvrgE9w",
          PLAN_ID: "P-7U340289BA306012CNLQF4BI",
          DIGEST_FORM_ACTION: "",
          DIGEST_MAILTO: "mailto:you@example.com?subject=old"
        };
        """
        rendered = build_site.render_config(existing, "e31e1b36d2727e090f84fe9c60ab2c15")
        self.assertIn("BAAb5cq2I0Xx3lFhRJNBjnuGCVT5VDtWfWHgAuSasCoaA_F4cFzLmDWcDmYhsXG6panQVSaRPR3gvrgE9w", rendered)
        self.assertNotIn("PLAN_ID", rendered)
        self.assertNotIn("P-7U340289BA306012CNLQF4BI", rendered)
        self.assertNotIn("subscription", rendered.lower())
        self.assertIn("mailto:nidhi69n@gmail.com?subject=PolicyPulse%20digest", rendered)
        self.assertIn("pro/e31e1b36d2727e090f84fe9c60ab2c15/", rendered)
        self.assertNotIn("example.com", rendered)


if __name__ == "__main__":
    unittest.main()
