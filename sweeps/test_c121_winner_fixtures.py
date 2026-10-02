"""Fail-closed evidence parsing and source-isolated fixture staging."""
import tempfile
import json
from pathlib import Path
import unittest

from sweeps.run_c121_winner_fixtures import markers, stage, cached_libraries


class WinnerFixtureTests(unittest.TestCase):
    def test_empty_log_does_not_validate(self):
        evidence = markers("")
        self.assertFalse(evidence["checks"]["matrix_cases"])
        self.assertFalse(evidence["checks"]["live_exposed"])
        self.assertIsNone(evidence["eligible_share"])

    def test_duplicate_or_missing_case_fails(self):
        line = "C121_WINNER_MATRIX case=1 cap=1 mail=0 mode=0 aaa=0 stable=1 eligible=1 old_ops=4000 new_ops=2200 pass=1"
        self.assertFalse(markers(line + "\n" + line)["checks"]["matrix_cases"])

    def test_distribution_keeps_mail_and_topology(self):
        log = "\n".join([
            "C121_WINNER_LIVE arm=newpair cap=1 mail=unknown eligible=1 stable=1 full_ops=4000 copy_ops=30 pass=1",
            "C121_WINNER_LIVE arm=hubsite cap=2 mail=zero eligible=0 stable=1 full_ops=8000 copy_ops=-1 pass=1",
            "C121_WINNER_LIVE arm=newpair cap=1 mail=unknown eligible=0 stable=0 full_ops=4000 copy_ops=-1 pass=1",
        ])
        e = markers(log)
        self.assertEqual((e["live_count"], e["eligible_count"]), (3, 1))
        self.assertEqual(e["eligible_full_ops"], 4000)
        self.assertEqual(e["eligible_copy_ops"], 30)
        self.assertEqual(len(e["distribution"]), 2)

    def test_assertion_is_not_hidden_by_success_marker(self):
        self.assertFalse(markers("C121_WINNER_ASSERT bad\nC121_WINNER_VM complete=1 cases=72 restored=1")["checks"]["no_fixture_assertion"])

    def test_staging_changes_copy_only(self):
        root = Path(__file__).resolve().parents[1]
        before = (root / "ai/OpexAI/main.nut").read_bytes()
        with tempfile.TemporaryDirectory() as folder:
            staged = stage(Path(folder))
            text = (staged / "main.nut").read_text(encoding="utf-8")
            self.assertEqual(text.count('require("c121_winner_vm.nut");'), 1)
            self.assertEqual(text.count("  FxWStart(this);"), 1)
        self.assertEqual((root / "ai/OpexAI/main.nut").read_bytes(), before)

    def test_wrong_library_groups_refused(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            manifest = root / "manifest.json"
            manifest.write_text(json.dumps({"libraries": []}), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "two library groups"):
                cached_libraries(manifest, root, root / "copy")

    def test_cached_library_hash_mismatch_refused(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            (root / "bananas").mkdir()
            (root / "bananas/bad.tar").write_bytes(b"wrong bytes")
            groups = [{"requested_name": name, "resolved": [{"filename": "bad.tar", "sha256": "bad"}]}
                      for name in ("Queue.FibonacciHeap", "Pathfinder.Rail")]
            manifest = root / "manifest.json"
            manifest.write_text(json.dumps({"libraries": groups}), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "hash mismatch"):
                cached_libraries(manifest, root, root / "copy")

    def test_library_path_traversal_refused(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            groups = [{"requested_name": name, "resolved": [{"filename": "../bad.tar", "sha256": "bad"}]}
                      for name in ("Queue.FibonacciHeap", "Pathfinder.Rail")]
            manifest = root / "manifest.json"
            manifest.write_text(json.dumps({"libraries": groups}), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "filename"):
                cached_libraries(manifest, root, root / "copy")


if __name__ == "__main__":
    unittest.main()
