"""Integrity checks for the versioned review evidence archive."""

from __future__ import annotations

import gzip
import json
from pathlib import Path
import unittest

from sweeps import package_review_evidence as package


ROOT = Path(__file__).resolve().parents[1]
INDEX = ROOT / "evidence" / "review" / "index.json"


class ReviewEvidenceTest(unittest.TestCase):
    def test_index_covers_every_cited_review_result(self):
        index = json.loads(INDEX.read_text(encoding="utf-8"))
        self.assertEqual(index["schema"], "opex-review-evidence-v1")
        self.assertEqual(index["missing"], [])
        indexed = {entry["source"] for entry in index["artifacts"]}
        self.assertEqual(indexed, set(package.cited_results()))

    def test_archives_match_recorded_hashes_and_are_deterministic(self):
        index = json.loads(INDEX.read_text(encoding="utf-8"))
        evidence_paths = [entry["evidence"] for entry in index["artifacts"]]
        self.assertEqual(len(evidence_paths), len(set(evidence_paths)))
        self.assertGreater(len(evidence_paths), 0)

        for entry in index["artifacts"]:
            packed = (ROOT / entry["evidence"]).read_bytes()
            raw = gzip.decompress(packed)
            self.assertEqual(len(raw), entry["raw_bytes"], entry["source"])
            self.assertEqual(package.sha256(raw), entry["raw_sha256"], entry["source"])
            self.assertEqual(len(packed), entry["gzip_bytes"], entry["source"])
            self.assertEqual(package.sha256(packed), entry["gzip_sha256"], entry["source"])


if __name__ == "__main__":
    unittest.main()
