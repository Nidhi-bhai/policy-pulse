"""Unit tests for the brief, archive merge, and parsers. No network."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from policypulse.archive import merge_all  # noqa: E402
from policypulse.sources import _RowParser, _pib_links, _sebi_circular_rows  # noqa: E402
from policypulse.tagger import annotate  # noqa: E402
from policypulse.text import parse_date, stable_id  # noqa: E402


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


if __name__ == "__main__":
    unittest.main()
