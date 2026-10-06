import tempfile
from pathlib import Path
import unittest
from sweeps.run_c121_fusion_fixtures import ROOT, prototype, stage, markers


class FusionTests(unittest.TestCase):
    def test_candidate_preserves_scan_and_argmax(self):
        source = (ROOT / "ai/OpexAI/air_economics_c121.nut").read_text(encoding="utf-8")
        candidate = prototype(source)
        for line in source.splitlines():
            if "profitAnnual > best.profitAnnual" in line or "score > scoreBest.score" in line:
                self.assertIn(line, candidate)
        self.assertIn("for (local planes = firstPlanes; planes <= maxAllowed; planes++)", candidate)
        self.assertTrue("openingOut.initial = FxFFinalize(clone best, clone scoreBest, decisionKDec, 1)" in candidate
                        or "openingOut.initial = FxFOpeningEconomics(clone best, clone scoreBest, decisionKDec)" in candidate)
        self.assertIn("openingOut.initial.decisionEconomics.engineMailKnown <- mailKnown", candidate)

    def test_source_drift_fails_closed(self):
        source = (ROOT / "ai/OpexAI/air_economics_c121.nut").read_text(encoding="utf-8")
        with self.assertRaises(ValueError):
            prototype(source.replace("    if (decisionOnly && fixedPlanes <= 0 && planes < maxAllowed && scoreBest != null", "    if (changed_contract)"))

    def test_staging_keeps_witness_byte_exact(self):
        original = (ROOT / "ai/OpexAI/air_economics_c121.nut").read_bytes()
        with tempfile.TemporaryDirectory() as folder:
            target = stage(Path(folder))
            self.assertEqual((target / "air_economics_c121.nut").read_bytes(), original)
            self.assertTrue((target / "c121_fusion_candidate.nut").is_file())
            self.assertIn("[1, 6, 13]", (target / "c121_winner_vm.nut").read_text())
        self.assertEqual((ROOT / "ai/OpexAI/air_economics_c121.nut").read_bytes(), original)

    def test_no_log_no_validation(self):
        self.assertFalse(all(markers("")["checks"].values()))

    def test_unstable_live_sample_excluded(self):
        log = "\n".join([
            "C121_FUSION_LIVE arm=newpair cap=9 mail=unknown checked=0 old_ops=30000 new_ops=28000 pass=1",
            "C121_FUSION_LIVE arm=hubsite cap=8 mail=positive checked=1 old_ops=20000 new_ops=17000 pass=1"])
        evidence = markers(log)
        self.assertEqual(evidence["live_count"], 2)
        self.assertEqual(evidence["checked_count"], 1)
        self.assertEqual((evidence["old_ops"], evidence["new_ops"]), (20000, 17000))

    def test_missing_matrix_domain_fails(self):
        log = "C121_WINNER_MATRIX case=1 cap=1 mail=0 mode=0 aaa=0 stable=1 eligible=1 old_ops=4 new_ops=3 pass=1"
        self.assertFalse(markers(log)["checks"]["matrix_domain"])


if __name__ == "__main__":
    unittest.main()
