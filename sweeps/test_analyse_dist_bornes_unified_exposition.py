"""Exposure gate must fail closed on unproven and unconstructed freight."""

import tempfile
import unittest
from pathlib import Path

from analyse_dist_bornes_unified_exposition import assess, read_log


def script_line(date, label, fields):
    return f"[log] [script:4] [0] [I] OPEX {date} {label} {fields}\n"


def fixture(distance):
    return "".join((
        script_line("1970-1-4", "EPOCH_BOUNDS",
                    "roadMin=7 railMin=7 railMax=200 airMin=200"),
        script_line("1970-2-1", "V276_PUBLISH",
                    "unit=0 evaluated=50 kept=20 mode=rail cargo=1 band=0"),
        script_line("1970-2-2", "PROJECT_CHOSEN",
                    f"rank=0 mode=rail kind=freight cargo=COAL src=12 dst=30 dist={distance}"),
        script_line("1970-2-3", "RAIL_ATTEMPT",
                    f"src=12 dst=30 kind=freight manh={distance} ok=1 reason=OK"),
        script_line("1970-2-3", "RAIL_BUILD",
                    f"line=1 src=12 dst=30 cargo=COAL dist={distance} trains=1"),
    ))


class DistBornesExposureAuditTest(unittest.TestCase):
    def test_reconstruct_physical_success_and_v276_band(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "sample.log"
            path.write_text(fixture(201), encoding="utf-8")
            data = read_log(path)
            self.assertEqual(data["rail_builds"], 1)
            self.assertEqual(len(data["raw_builds"]), 1)
            self.assertTrue(data["raw_builds"][0]["outside_historical_v276"])
            self.assertEqual(data["v276_publishes"], 1)
            self.assertEqual(len(data["freight_joined"]), 1)
            self.assertTrue(data["freight_joined"][0]["outside_historical_v276"])
            path.write_text(fixture(200), encoding="utf-8")
            self.assertFalse(read_log(path)["freight_joined"][0]["outside_historical_v276"])

    def test_missing_and_unlinked_are_inconclusive(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            self.assertEqual(assess(root, [42])["verdict"], "INCONCLUSIVE")
            (root / "reference_seed42_r0.log").write_text("", encoding="utf-8")
            (root / "dist_bornes_unified_seed42_r0.log").write_text(fixture(201), encoding="utf-8")
            report = assess(root, [42])
            self.assertEqual(report["verdict"], "INCONCLUSIVE")
            self.assertEqual(report["unlinked_potential_seeds"], [42])
            (root / "dist_bornes_unified_seed42_r0.log").write_text(fixture(200), encoding="utf-8")
            self.assertEqual(assess(root, [42])["verdict"], "NO_GO_NON_EXPOSE")

    def test_no_chosen_pair_means_no_proof_of_construction(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "broken.log"
            path.write_text(fixture(201).replace("PROJECT_CHOSEN", "OTHER_EVENT"), encoding="utf-8")
            self.assertEqual(read_log(path)["freight_joined"], [])


if __name__ == "__main__":
    unittest.main()
