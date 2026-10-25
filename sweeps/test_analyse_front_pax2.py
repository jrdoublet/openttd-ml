"""Contrats du decodeur FRONT-PAX-2, sans NoAI/Docker ni logs externes."""

from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from analyse_front_pax2 import ARMS, analyze, parse_line, render_md


ARRAYS = ("seen", "short", "below_min", "blocked_min", "below_airmax",
          "below_plane", "below_config", "below_within", "other_band",
          "airmax", "band_pass")


def row(arm, scan=1, *, scan_year=1970, emitted_year=1972, n=4):
    data = {name: [0, 0, 0, 0] for name in ARRAYS}
    data["seen"][2] = n
    data["below_min"][2] = n
    data["blocked_min"][2] = n
    data["below_within"][2] = n
    fields = (f"scan={scan} year={scan_year} arm={arm} pax_band=0 "
              f"air_min=200 air_max=512 under20=2 ")
    fields += " ".join(f"{key}={','.join(map(str, data[key]))}" for key in ARRAYS)
    return f"[engine] OPEX {emitted_year}-4-6 FRONT_PAX2 {fields}\n"


class FrontPax2DecoderTests(unittest.TestCase):
    def test_real_schema_includes_under20_and_four_bins(self):
        parsed = parse_line(row("newpair"), "synthetic.log", 1)
        self.assertEqual(parsed["under20"], 2)
        self.assertEqual(parsed["scan_year"], 1970)
        self.assertEqual(parsed["emitted_year"], 1972)
        self.assertEqual(parsed["seen"], (0, 0, 4, 0))

    def test_completed_and_censored_scans_are_not_confused(self):
        with TemporaryDirectory() as folder:
            log = Path(folder) / "sample.log"
            log.write_text("OPEX 1970-1-2 AIR_PLAN_INPUT scan=1 combos=1\n"
                           + "OPEX 1971-1-2 AIR_PLAN_INPUT scan=2 combos=1\n"
                           + "".join(row(arm) for arm in ARMS), encoding="utf-8")
            report = analyze([log])
        self.assertEqual(report["problems"], [])
        self.assertEqual(report["started_scans"], 2)
        self.assertEqual(report["complete_scans"], 1)
        self.assertEqual(report["censored_scans"], 1)
        self.assertEqual(report["records"], 3)
        self.assertEqual(report["all"]["below_min"], [0, 0, 12, 0])
        self.assertEqual(report["by_arm"]["newpair"]["blocked_min"], [0, 0, 4, 0])
        self.assertEqual(report["by_scan_year"]["1970"]["below_min"], [0, 0, 12, 0])
        self.assertEqual(report["by_emitted_year"]["1972"]["below_min"], [0, 0, 12, 0])
        self.assertEqual(report["coverage_by_file_year"][0]["completed"], 1)
        self.assertEqual(report["coverage_by_file_year"][1]["censored"], 1)
        self.assertIn("cycles complets : 1/2", render_md(report))

    def test_partial_three_arms_are_reported_and_excluded_from_totals(self):
        with TemporaryDirectory() as folder:
            log = Path(folder) / "partial.log"
            log.write_text("OPEX 1970-1-1 AIR_PLAN_INPUT scan=1 combos=1\n"
                           + row("newpair") + row("hubsite"), encoding="utf-8")
            report = analyze([log])
        self.assertEqual(report["complete_scans"], 0)
        self.assertEqual(report["censored_scans"], 1)
        self.assertEqual(report["records"], 0)
        self.assertTrue(any("attendu 3 bras" in p for p in report["problems"]))
        self.assertEqual(report["all"]["below_min"], [0, 0, 0, 0])

    def test_invalid_partition_and_negative_bins_rejected(self):
        line = row("newpair")
        with self.assertRaisesRegex(ValueError, "seen non partitionne"):
            parse_line(line.replace("blocked_min=0,0,4,0", "blocked_min=0,0,3,0"), "x", 1)
        with self.assertRaisesRegex(ValueError, "quatre entiers"):
            parse_line(line.replace("seen=0,0,4,0", "seen=-1,0,4,0"), "x", 1)


if __name__ == "__main__":
    unittest.main()
