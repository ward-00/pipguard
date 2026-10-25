"""Uji unit rekonstruksi metadata historis (python3 -m unittest discover scripts/eval)."""
import unittest
from datetime import timedelta

import pypi_history as ph

T0 = ph.parse_time("2024-03-01 10:00:00.000")


def v(version, minutes, **kw):
    r = {"norm_name": "pkg", "version": version, "upload_time": T0 + timedelta(minutes=minutes),
         "summary": "", "home_page": "", "project_urls": [], "description_len": 0,
         "classifier_count": 0, "requires_dist_count": 0, "first_built_upload": None}
    r.update(kw)
    return r


class SnapshotTest(unittest.TestCase):
    def test_first_scenario_sees_only_first_minute(self):
        vs = [v("0.1", 0), v("0.2", 0.5, summary="later summary"), v("1.0", 60 * 24 * 40, home_page="https://x")]
        s = ph.snapshot(vs, ph.as_of_time(vs, "first"))
        self.assertEqual(s["release_count"], 2)
        self.assertEqual(s["summary"], "later summary")  # rilis terbaru pada as_of
        self.assertFalse(s["has_homepage"])
        self.assertEqual(s["first_release"], "2024-03-01T10:00:00Z")

    def test_last_scenario_sees_everything(self):
        vs = [v("0.1", 0), v("1.0", 60 * 24 * 40, home_page="https://x")]
        s = ph.snapshot(vs, ph.as_of_time(vs, "last"))
        self.assertEqual(s["release_count"], 2)
        self.assertTrue(s["has_homepage"])

    def test_first_malicious_version_of_hijacked_project(self):
        vs = [v("1.0", 0, project_urls=["Source, https://github.com/a/b"]), v("1.1", 60 * 24 * 365)]
        s = ph.snapshot(vs, ph.as_of_time(vs, "first", first_malicious=vs[1]["upload_time"]))
        self.assertEqual(s["release_count"], 2)  # rilis sah sebelumnya terlihat
        self.assertEqual(s["first_release"], "2024-03-01T10:00:00Z")

    def test_reported_never_before_attack(self):
        vs = [v("0.1", 0)]
        early_report = T0 - timedelta(hours=3)
        self.assertEqual(ph.as_of_time(vs, "reported", reported=early_report), T0 + timedelta(minutes=1))

    def test_sdist_only_depends_on_time(self):
        vs = [v("0.1", 0, first_built_upload=T0 + timedelta(minutes=10))]
        self.assertTrue(ph.snapshot(vs, T0 + timedelta(minutes=1))["sdist_only"])
        self.assertFalse(ph.snapshot(vs, T0 + timedelta(minutes=11))["sdist_only"])

    def test_repository_detection_matches_go_keys(self):
        self.assertTrue(ph.has_repository(["Source Code, https://github.com/a/b"]))
        self.assertFalse(ph.has_repository(["Documentation, https://docs"]))
        self.assertFalse(ph.has_repository(["Source, "]))

    def test_compact_rows_use_total_version_count(self):
        # Hasil fetch compact: versi tengah hilang, n_versions membawa jumlahnya.
        vs = [v("0.1", 0, n_versions=7), v("2.0", 60 * 24 * 90, n_versions=7)]
        self.assertEqual(ph.snapshot(vs, ph.as_of_time(vs, "last"))["release_count"], 7)
        self.assertEqual(ph.snapshot(vs, ph.as_of_time(vs, "first"))["release_count"], 1)

    def test_group_versions_parses_clickhouse_strings(self):
        rows = [{"norm_name": "a", "version": "2", "upload_time": "2024-01-02 00:00:00.000",
                 "first_built_upload": "1970-01-01 00:00:00.000"},
                {"norm_name": "a", "version": "1", "upload_time": "2024-01-01 00:00:00.000",
                 "first_built_upload": "2024-01-01 00:00:05.000"}]
        g = ph.group_versions(rows)["a"]
        self.assertEqual([x["version"] for x in g], ["1", "2"])
        self.assertIsNone(g[1]["first_built_upload"])
        self.assertIsNotNone(g[0]["first_built_upload"])

    def test_sql_list_rejects_unnormalised_names(self):
        with self.assertRaises(ValueError):
            ph._sql_list(["ok-name", "bad'name"])


if __name__ == "__main__":
    unittest.main()
