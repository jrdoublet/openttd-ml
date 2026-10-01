"""Integrity checks for the versioned review evidence archive."""

from __future__ import annotations

import gzip
import contextlib
import io
import json
from pathlib import Path
import tempfile
import unittest

from sweeps import package_review_evidence as package


ROOT = Path(__file__).resolve().parents[1]
INDEX = ROOT / "evidence" / "review" / "index.json"


class ReviewEvidenceTest(unittest.TestCase):
    def test_historical_index_is_a_snapshot_not_global_coverage(self):
        index = json.loads(INDEX.read_text(encoding="utf-8"))
        self.assertEqual(index["schema"], "opex-review-evidence-v1")
        self.assertEqual(index["missing"], [])
        sources = [entry["source"] for entry in index["artifacts"]]
        self.assertEqual(len(sources), len(set(sources)))
        self.assertTrue(all(s.startswith("results/") for s in sources))
        # Current coverage is a separate audit, expected to report missing inputs
        # without the recent VPS results. Integrity is not citation coverage.

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


class ReviewEvidencePackagingTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)

    def put(self, rel, text):
        path = self.root / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")
        return path

    def invoke(self, *args):
        with contextlib.redirect_stdout(io.StringIO()):
            return package.main(list(args), root=self.root)

    def seed_archive(self):
        self.put("docs/taches.md", "`results/c121_new.json`")
        source = self.put("results/c121_new.json", '{"value": 1}\n')
        self.assertEqual(self.invoke("--write"), 0)
        return source

    def test_discovers_recent_prefixes_journals_and_nested_paths(self):
        self.put("docs/43_c121.md", "`results/c121_new.json` `results/c121_new.json`")
        self.put("docs/journaux/today.md", "results/c122/run.manifest.json")
        self.put("docs/archives/old.md", "results/old.json")
        self.put("AGENTS.md", "results/c115.json")
        self.put("ai/OpexAI/CLAUDE.md", "results/c119.json")
        self.assertEqual(package.cited_results(self.root), [
            "results/c115.json", "results/c119.json", "results/c121_new.json",
            "results/c122/run.manifest.json", "results/old.json"])

    def test_does_not_truncate_jsonl_or_compressed_references(self):
        self.put("docs/test.md", "results/a.jsonl results/b.json.gz results/c.json")
        self.assertEqual(package.cited_results(self.root), ["results/c.json"])

    def test_missing_recent_result_is_reported_without_writes(self):
        self.put("docs/test.md", "results/c122_missing.json")
        self.assertEqual(package.audit(self.root)["missing"], ["results/c122_missing.json"])
        self.assertEqual(self.invoke("--write"), 2)
        self.assertFalse((self.root / "evidence").exists())

    def test_default_audit_reports_unarchived_without_writes(self):
        self.put("docs/test.md", "results/c121.json")
        self.put("results/c121.json", "{}")
        self.assertEqual(package.audit(self.root)["pending"], ["results/c121.json"])
        self.assertEqual(self.invoke(), 2)
        self.assertFalse((self.root / "evidence").exists())

    def test_verified_archive_reused_without_local_results(self):
        self.seed_archive().unlink()
        self.assertEqual(self.invoke(), 0)
        self.assertEqual(self.invoke("--write"), 0)

    def test_missing_new_input_preserves_existing_index(self):
        self.seed_archive()
        index = self.root / "evidence/review/index.json"
        before = index.read_bytes()
        self.put("docs/new.md", "results/c122_missing.json")
        self.assertEqual(self.invoke("--write"), 2)
        self.assertEqual(index.read_bytes(), before)

    def test_conflicting_local_result_is_never_promoted(self):
        source = self.seed_archive()
        index = self.root / "evidence/review/index.json"
        before = index.read_bytes()
        source.write_text('{"value": 2}', encoding="utf-8")
        self.assertTrue(package.audit(self.root)["errors"])
        self.assertEqual(self.invoke("--write"), 2)
        self.assertEqual(index.read_bytes(), before)

    def test_same_basename_different_subdirectories_is_safe(self):
        self.put("docs/test.md", "results/a/run.json results/b/run.json")
        self.put("results/a/run.json", '{"a": 1}')
        self.put("results/b/run.json", '{"b": 2}')
        self.assertEqual(self.invoke("--write"), 0)
        self.assertEqual(len(package.audit(self.root)["entries"]), 2)
        self.assertEqual(self.invoke(), 0)

    def test_tampered_archive_fails(self):
        self.seed_archive()
        entry = package.audit(self.root)["entries"][0]
        (self.root / entry["evidence"]).write_bytes(b"not gzip")
        self.assertTrue(package.audit(self.root)["errors"])
        self.assertEqual(self.invoke("--write"), 2)

    def test_path_traversal_fails(self):
        self.put("docs/test.md", "results/../secret.json")
        self.assertTrue(package.audit(self.root)["errors"])
        self.assertEqual(self.invoke("--write"), 2)

    def test_deterministic_gzip(self):
        raw = b'{"value": 1}\n'
        packed = package.gzip_deterministic(raw)
        self.assertEqual(packed, package.gzip_deterministic(raw))
        self.assertEqual(gzip.decompress(packed), raw)
        self.assertEqual(packed[4:8], b"\x00\x00\x00\x00")


if __name__ == "__main__":
    unittest.main()
