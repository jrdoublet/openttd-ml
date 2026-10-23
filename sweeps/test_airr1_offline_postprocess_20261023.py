"""Contrats synthétiques du post-traitement AIRR1, sans logs ni moteur."""

import json
from pathlib import Path
import sys
from tempfile import TemporaryDirectory
import types
import unittest
from unittest.mock import patch

# ``recover`` imports the real benchmark comparison/health code, whose bench_v2
# module imports openttdlab at collection time. The standalone pytest venv has
# no OpenTTDLab, although offline comparisons do not call its engine APIs.
# Follow the project's test-only adapter convention: preserve real imports
# whenever present; otherwise make engine access fail loudly rather than
# substituting MagicMock results that could silently validate a broken run.
try:
    import openttdlab  # noqa: F401
except ModuleNotFoundError as error:
    if error.name != "openttdlab":
        raise

    def _no_engine(*_args, **_kwargs):
        raise RuntimeError("OpenTTDLab is required for engine execution")

    stub = types.ModuleType("openttdlab")
    for name in ("bananas_ai", "bananas_ai_library", "local_folder", "run_experiments"):
        setattr(stub, name, _no_engine)
    sys.modules["openttdlab"] = stub

import recover_air_roi_renfort1_itt_campaign2_20261022 as recover
import report_air_roi_renfort1_itt_20261022 as report
import report_air_roi_renfort1_itt_campagne2_20261022 as report2


class TestAirR1OfflinePostprocessing(unittest.TestCase):
    def test_recovery_refuses_wrong_campaign_identity(self):
        with TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "fixture.manifest.json").write_text(json.dumps({
                "campaign_id": "another_campaign",
                "execution": {"options": {"campaign": "fixture"}},
                "source_bundle": {"sha256": "test_bundle"},
            }), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "Campaign identity mismatch"):
                recover.recover("fixture", root, write=True)
            self.assertFalse((root / "fixture.json").exists())

    def test_recovery_refuses_checkpoint_from_another_bundle(self):
        with TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "fixture.manifest.json").write_text(json.dumps({
                "campaign_id": "fixture",
                "execution": {"options": {
                    "campaign": "fixture", "years": 10, "repeats": 1,
                    "seeds": list(range(20)),
                }},
                "source_bundle": {"sha256": "expected_bundle"},
            }), encoding="utf-8")
            (root / "fixture.jsonl").write_text(json.dumps({
                "campaign_id": "fixture", "source_bundle_sha256": "other_bundle",
            }) + "\n", encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "Checkpoint source mismatch"):
                recover.recover("fixture", root, write=True)
            self.assertFalse((root / "fixture.json").exists())

    def test_report_uses_seed_level_bootstrap(self):
        self.assertEqual(report.paired_ci([0.0, 0.0, 0.0], replays=100), [0.0, 0.0])
        self.assertEqual(report.summary([None, 4, 2])["mean"], 3)

    def test_campaign2_refuses_incomplete_panel_without_writing(self):
        with TemporaryDirectory() as directory:
            root = Path(directory)
            out = root / "results"
            out.mkdir()
            doc = root / "history-copy.md"
            fixture = {"games_completed": 39, "games_total": 40,
                       "pairs_complete": 20, "comparison_complete": False}
            argv = ["report2", "--campaign", "fixture", "--results-dir", str(out),
                    "--doc", str(doc)]
            with patch.object(report2, "analyze_campaign", return_value=fixture), \
                    patch.object(sys, "argv", argv):
                with self.assertRaisesRegex(ValueError, "Campagne incomplète"):
                    report2.main()
            self.assertFalse(doc.exists())
            self.assertFalse((out / "fixture_itt_report.json").exists())

    def test_campaign2_writes_only_explicit_outputs(self):
        with TemporaryDirectory() as directory:
            root = Path(directory)
            out = root / "results"
            out.mkdir()
            doc = root / "history-copy.md"
            fixture = {"games_completed": 40, "games_total": 40,
                       "pairs_complete": 20, "comparison_complete": True,
                       "scientific_verdict": "inconclusive"}
            argv = ["report2", "--campaign", "fixture", "--results-dir", str(out),
                    "--doc", str(doc)]
            with patch.object(report2, "analyze_campaign", return_value=fixture), \
                    patch.object(report2, "render", return_value="Synthetic report\n"), \
                    patch.object(sys, "argv", argv):
                report2.main()
            self.assertEqual(doc.read_text(encoding="utf-8"), "Synthetic report\n")
            payload = json.loads((out / "fixture_itt_report.json").read_text(encoding="utf-8"))
            self.assertEqual(payload["scientific_verdict"], "inconclusive")


if __name__ == "__main__":
    unittest.main()
