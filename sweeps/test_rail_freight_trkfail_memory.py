"""Contract for isolated persistent-geometry freight failure memory."""
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1] / "ai" / "OpexAI"

class FreightTrkfailMemoryContract(unittest.TestCase):
    def test_setting_disabled_for_every_difficulty(self):
        info = (ROOT / "info.nut").read_text(encoding="utf-8")
        cfg = info.split('name = "rail_freight_trkfail_memory",', 1)[1].split("});", 1)[0]
        for level in ("easy", "medium", "hard", "custom"):
            self.assertRegex(cfg, rf"\b{level}_value\s*=\s*0\b")
        self.assertIn("RAIL_FREIGHT_TRKFAIL_MEMORY <- false;",
                      (ROOT / "globals_pre.nut").read_text(encoding="utf-8"))
        self.assertIn('RAIL_FREIGHT_TRKFAIL_MEMORY = AIController.GetSetting("rail_freight_trkfail_memory") != 0;',
                      (ROOT / "settings.nut").read_text(encoding="utf-8"))

    def test_uses_the_existing_strict_geometry_signature(self):
        builder = (ROOT / "builder_rail.nut").read_text(encoding="utf-8")
        rail = (ROOT / "task_rail.nut").read_text(encoding="utf-8")
        self.assertIn('RAIL_FREIGHT_TRKFAIL_MEMORY && candidate.kind == "freight"', builder)
        self.assertIn('RAIL_FREIGHT_TRKFAIL_MEMORY && candidate.kind == "freight"', rail)
        predicate = builder.split("function OpexRailTrackFailureIsPersistentGeometry(", 1)[1].split(
            "function OpexJoinPathIsDedicated(", 1)[0]
        self.assertIn("AIError.ERR_AREA_NOT_CLEAR", predicate)
        self.assertIn("failure.is_station != 1", predicate)
        self.assertIn("failure.owner_self != 1", predicate)
        self.assertIn("failure.tile == leadA || failure.tile == leadB", predicate)
        path_predicate = builder.split("function OpexRailTrackFailureIsPersistentPathLead(", 1)[1].split(
            "function OpexJoinPathIsDedicated(", 1)[0]
        self.assertIn("AIError.ERR_AREA_NOT_CLEAR", path_predicate)
        self.assertIn("failure.is_station != 1", path_predicate)
        self.assertIn("failure.owner_self != 1", path_predicate)
        self.assertIn("failure.index == 1 && failure.tile == tiles[1]", path_predicate)
        self.assertIn("failure.index == last - 1 && failure.tile == tiles[last - 1]", path_predicate)
        self.assertIn("this._markPairAbandoned(OpexAbandonedPairKey(candidate))", rail)

if __name__ == "__main__":
    unittest.main()
