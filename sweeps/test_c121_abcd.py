from pathlib import Path
import shutil
import tempfile
import unittest

from sweeps.diag_c121_abcd import ARMS, ROOT, marker, stage_copy


class C121ABCDTests(unittest.TestCase):
    def test_matrix_has_all_independent_combinations(self):
        self.assertEqual(
            {(v["c121_air_economics"], v["c121_catalog_incremental"]) for v in ARMS.values()},
            {(0, 0), (0, 1), (1, 0), (1, 1)},
        )

    def test_copy_decouples_catalog_without_touching_production(self):
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp) / "OpexAI"
            stage_copy(target)
            settings = (target / "settings.nut").read_text(encoding="utf-8")
            self.assertIn(
                'C121_CATALOG_INCREMENTAL = AIController.GetSetting("c121_catalog_incremental") != 0;',
                settings,
            )
            self.assertNotIn(
                'C121_CATALOG_INCREMENTAL = C121_AIR_ECONOMICS\n'
                '      && AIController.GetSetting("c121_catalog_incremental") != 0;',
                settings,
            )
            self.assertIn("C121ABCDSource();", (target / "main.nut").read_text(encoding="utf-8"))
        production = (ROOT / "ai/OpexAI/settings.nut").read_text(encoding="utf-8")
        self.assertIn("C121_CATALOG_INCREMENTAL = C121_AIR_ECONOMICS", production)

    def test_marker_keeps_owner_and_effective_values(self):
        text = "[script:4] [0] [I] C121_ABCD v=1 econ=0 catalog=1 c115=1"
        self.assertEqual(marker(text), [{"owner": 0, "v": "1", "econ": "0", "catalog": "1", "c115": "1"}])


if __name__ == "__main__":
    unittest.main()
