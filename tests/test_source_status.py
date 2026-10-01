import json
import os
import tempfile
import unittest
from unittest.mock import patch
from urllib.error import URLError

import build_dashboard
import scanner


class FetchStatusTests(unittest.TestCase):
    @patch("scanner.time.sleep")
    @patch("scanner._fetch_once", return_value=[])
    def test_repeated_empty_feed_is_not_reported_as_no_news(self, fetch_once, _sleep):
        result = scanner.fetch_rss("freight risk", retries=2)

        self.assertEqual(result["status"], "empty_unverified")
        self.assertEqual(result["items"], [])
        self.assertEqual(result["attempts"], 3)

    @patch("scanner.time.sleep")
    @patch("scanner._fetch_once", side_effect=URLError("offline"))
    def test_request_errors_are_unavailable(self, fetch_once, _sleep):
        result = scanner.fetch_rss("freight risk", retries=1)

        self.assertEqual(result["status"], "unavailable")
        self.assertEqual(result["error_type"], "URLError")
        self.assertEqual(result["attempts"], 2)

    @patch("scanner.time.sleep")
    @patch("scanner._fetch_once", side_effect=[URLError("retry"), [{"title": "headline", "link": "https://example.test/1", "pub_date": "", "source": "Example"}]])
    def test_success_after_retry_is_available(self, fetch_once, _sleep):
        result = scanner.fetch_rss("freight risk", retries=1)

        self.assertEqual(result["status"], "ok")
        self.assertEqual(result["attempts"], 2)
        self.assertEqual(len(result["items"]), 1)


class ScanStatusTests(unittest.TestCase):
    def test_partial_sources_make_the_run_partial(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            signals_path = os.path.join(temp_dir, "signals.json")
            with patch.object(scanner, "DATA_DIR", temp_dir), patch.object(scanner, "SIGNALS_PATH", signals_path), patch.object(
                scanner,
                "CATEGORIES",
                {"Example": {"queries": [{"q": "test query", "lang": "en"}], "severity": "low", "escalate_if": []}},
            ), patch.object(
                scanner,
                "fetch_rss",
                return_value={"status": "empty_unverified", "items": [], "attempts": 3, "error_type": None},
            ), patch("scanner.time.sleep"):
                result = scanner.run_scan()

            self.assertEqual(result["runs"][-1]["status"], "partial")
            self.assertEqual(result["runs"][-1]["empty_unverified_sources"], 1)
            with open(signals_path, encoding="utf-8") as file:
                saved = json.load(file)
            self.assertEqual(saved["runs"][-1]["sources"][0]["status"], "empty_unverified")

    def test_dashboard_distinguishes_partial_scans_and_legacy_runs(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            state_path = os.path.join(temp_dir, "signals.json")
            index_path = os.path.join(temp_dir, "index.html")
            dashboard_path = os.path.join(temp_dir, "dashboard.html")
            with open(state_path, "w", encoding="utf-8") as file:
                json.dump({"signals": [], "runs": [{
                    "timestamp": "2026-09-29T10:00:00+00:00",
                    "status": "partial",
                    "empty_unverified_sources": 2,
                    "unavailable_sources": 1,
                }]}, file)
            with patch.object(build_dashboard, "SIGNALS_PATH", state_path), patch.object(build_dashboard, "INDEX_PATH", index_path), patch.object(build_dashboard, "DASHBOARD_PATH", dashboard_path):
                build_dashboard.build()
            with open(index_path, encoding="utf-8") as file:
                html = file.read()
            self.assertIn("Partial scan", html)
            self.assertIn("empty feed(s) unverified", html)
            self.assertIn("unavailable source(s)", html)

            with open(state_path, "w", encoding="utf-8") as file:
                json.dump({"signals": [], "runs": [{"timestamp": "2026-09-28T10:00:00+00:00"}]}, file)
            with patch.object(build_dashboard, "SIGNALS_PATH", state_path), patch.object(build_dashboard, "INDEX_PATH", index_path), patch.object(build_dashboard, "DASHBOARD_PATH", dashboard_path):
                build_dashboard.build()
            with open(index_path, encoding="utf-8") as file:
                html = file.read()
            self.assertIn("Source status was not recorded for this historical scan", html)


if __name__ == "__main__":
    unittest.main()
