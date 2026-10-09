"""Contrats de la variante BFAIL : périmètre newpair et réglage inerte par défaut."""
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1] / "ai" / "OpexAI"


class BfailDisposalContract(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.source = {name: (ROOT / name).read_text(encoding="utf-8") for name in
                      ("globals_pre.nut", "info.nut", "settings.nut", "air_construction.nut", "air_recovery.nut")}

    def test_all_difficulties_default_off_and_loaded_once(self):
        setting = self.source["info.nut"].split('name = "air_bfail_dispose_orphan",', 1)[1].split("});", 1)[0]
        for field in ("easy", "medium", "hard", "custom"):
            self.assertIn(f"{field}_value = 0", setting)
        self.assertIn("AIR_BFAIL_DISPOSE_ORPHAN <- false;", self.source["globals_pre.nut"])
        self.assertIn('AIR_BFAIL_DISPOSE_ORPHAN = AIController.GetSetting("air_bfail_dispose_orphan") != 0;',
                      self.source["settings.nut"])

    def test_only_unreused_newpair_changes_and_calls_existing_recovery(self):
        construction = self.source["air_construction.nut"]
        failure = construction.split("if (airportB == null) {", 1)[1].split("if (PROBE_AIR_FINANCE_MARGIN && result.orphanRetained)", 1)[0]
        self.assertIn("&& !(AIR_BFAIL_DISPOSE_ORPHAN && !reuseA && !reuseB)", failure)
        self.assertIn("result.recoveryTraceId = OpexAirRollback(reuseA ? null : airportA, null, []);", failure)
        self.assertIn("else result.orphanRetained = !reuseA;", failure)
        self.assertIn('result.reason = reuseB ? "HUBB" : "BFAIL";', failure)

    def test_rollback_protects_airport_with_service(self):
        recovery = self.source["air_recovery.nut"]
        self.assertIn("if (!AICompany.IsMine(AITile.GetOwner(tile))) continue;", recovery)
        self.assertIn("AIVehicleList_Station(station)", recovery)
        self.assertIn("if (!used && AIAirport.RemoveAirport(tile)) continue;", recovery)


if __name__ == "__main__":
    unittest.main()
