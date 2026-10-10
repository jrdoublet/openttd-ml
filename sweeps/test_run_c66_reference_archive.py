"""Retained OpenTTD saves must never modify a fingerprinted campaign bundle."""

import sys
from pathlib import Path
import unittest


sys.path.insert(0, str(Path(__file__).parent))
from run_c66_reference import ROOT, container_archive_destination


class RetainedSavegameDestinationTests(unittest.TestCase):
    def test_relative_host_path_stays_outside_frozen_bundle(self):
        path = container_archive_destination(
            "results/my_campaign_saves", ROOT, "/work", "my_campaign")
        self.assertEqual(path, "/work/results/my_campaign_saves")

    def test_mounted_parent_includes_relative_checkout(self):
        path = container_archive_destination(
            "results/my_campaign_saves", ROOT.parent, "/work/" + ROOT.name,
            "my_campaign")
        self.assertEqual(path, "/work/" + ROOT.name + "/results/my_campaign_saves")

    def test_source_bundle_and_unmounted_destination_are_rejected(self):
        for path in ("results/my_campaign_bundle", "results/my_campaign_bundle/harness/saves"):
            with self.subTest(path=path), self.assertRaises(ValueError):
                container_archive_destination(path, ROOT, "/work", "my_campaign")
        with self.assertRaises(ValueError):
            container_archive_destination(ROOT.parent / "outside", ROOT, "/work", "my_campaign")


if __name__ == "__main__":
    unittest.main()
