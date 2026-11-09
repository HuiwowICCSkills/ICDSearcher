"""Offline tests for ICDSearcher."""
from __future__ import annotations

import argparse
import sys
import unittest
from pathlib import Path

from bs4 import BeautifulSoup

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

import icd_adapter as adapter  # noqa: E402


class FakeHttp:
    def __init__(self, html):
        self.html = html
        self.evidence = []

    def soup(self, url, params=None, headers=None):
        return BeautifulSoup(self.html, "html.parser"), {
            "source_url": "https://www.internationalcrimesdatabase.org/SearchResults/",
            "http_status": 200, "content_type": "text/html", "bytes": 100,
            "retrieved_at": "2026-11-09T00:00:00Z", "sha256": "0" * 64,
        }


def args(**kwargs):
    base = dict(limit=1, offset=0, no_term_fallback=True, cache=".cache",
                offline=False, cache_ttl=0, timeout=30)
    base.update(kwargs)
    return argparse.Namespace(**base)


class IcdTests(unittest.TestCase):
    def test_search_parses_case_row(self):
        html = """
        <html><body><div class="search-results">
          <h2>1 results (ordered by relevance)</h2>
          <strong><a href="/Case/919"><strong>Bugingo</strong> : Prosecutor v. Bugingo</a></strong>
          <p>ICTY, 1 January 2020</p>
          <div class="search-summary">Summary text</div>
        </div></body></html>
        """
        out = adapter.search("genocide", args(), FakeHttp(html))
        self.assertEqual(out["status"], "ok")
        self.assertEqual(out["total"], 1)
        self.assertEqual(out["results"][0]["case_name"], "Bugingo")
        self.assertIn("/Case/919", out["results"][0]["url"])


if __name__ == "__main__":
    unittest.main()
