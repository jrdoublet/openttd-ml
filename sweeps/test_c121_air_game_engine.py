"""Contrats statiques du raccourci C121 « avion de la partie »."""
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "sweeps"))

from analyse_c121_engine_table import parse_line, parse_log_text, reconstruct  # noqa: E402
from campaign_freeze import parse_ai_settings  # noqa: E402

AI = ROOT / "ai" / "OpexAI"
LAUNCHER = ROOT / "sweeps" / "diag_c121_game_engine.py"


def source(name):
    return (AI / name).read_text(encoding="utf-8")


class GameEngineContractTests(unittest.TestCase):
    def test_setting_defaults_to_on(self):
        # Adopte le 2026-10-03 par la regle de neutralite des optimisations
        # d'opcodes (20x10 neutre) ; inerte hors bras C121.
        # V237: the adopted path is permanent; the public rollback is gone.
        from v237_contracts import assert_retired
        assert_retired(self, ('c121_air_game_engine',))

    def test_global_and_c121_gated_load(self):
        from v237_contracts import assert_retired
        assert_retired(self, ("c121_air_game_engine",))
        self.assertIn("C121_GAME_ENGINE_STATE <- {};", source("globals_pre.nut"))
        self.assertNotIn("C121_GAME_ENGINE_STATE", source("persist.nut"))

    def test_shortcut_guard_and_constants(self):
        econ = source("air_economics_c121.nut")
        self.assertIn("const C121_GAME_ENGINE_STREAK = 8;", econ)
        self.assertIn("const C121_GAME_ENGINE_CHECK_EVERY = 32;", econ)
        chooser = econ.split("function OpexC121ChooseRoutePlane(", 1)[1]
        demand = chooser.index("OpexC121PrepareDemandShadow")
        static = chooser.index("OpexC121PrepareEngineStatic")
        guard = chooser.index("geState = OpexC121GameEngineState(airportType)")
        self.assertLess(demand, static)
        self.assertLess(static, guard)
        self.assertIn("OpexC121GameEngineTryShortcut", chooser)
        self.assertIn("geMode != 1", chooser)
        self.assertIn("OpexC121WinnerEconomics", chooser)
        self.assertIn("OpexC121ScanRoutePlaneEngines", chooser)

    def test_five_events_and_both_revision_invalidations(self):
        econ = source("air_economics_c121.nut")
        for event in ("establish", "check_ok", "check_miss", "reset", "fallback"):
            self.assertIn('OpexC121GameEngineLog("' + event + '"', econ)
        self.assertIn('AILog.Info(line)', econ)
        self.assertIn('"C121_GE event="', econ)
        self.assertIn("reason=engine_rev|learn_rev", econ)
        sync = econ.split("function OpexC121GameEngineSyncRevs", 1)[1].split("function ", 1)[0]
        self.assertIn("C121_CATALOG_AIRPORT_REV", sync)
        self.assertIn("C121_CATALOG_AIRPORT_LEARN_REV", sync)
        self.assertIn('"engine_rev"', sync)
        self.assertIn('"learn_rev"', sync)
        log = econ.split("function OpexC121GameEngineLog", 1)[1].split("function ", 1)[0]
        self.assertNotIn("if (!C121_AIR_GAME_ENGINE) return;", log)
        self.assertNotIn("PROBE_C121_ENGINE_TABLE", log)

    def test_launcher_paired_arms_and_extra_env(self):
        from sweeps import diag_c121_game_engine
        with self.assertRaisesRegex(SystemExit, "permanent"):
            diag_c121_game_engine.main()


class GameEngineProbeTokenTests(unittest.TestCase):
    def test_parser_reads_ge_tokens_and_defaults_old_lines(self):
        event = parse_line(
            "C121_ENGTAB_PLAN pass=1 date=1970-06-01 key=1-2-3-newpair arm=newpair "
            "ap=3 dist=10 paxRawA=50 paxRawB=50 paxA=50 paxB=50 mailRawA=0 mailRawB=0 "
            "eng=223 score=6 P=6 C=1000 dScore=6 dP=6 dC=1000 pfScore=-1 pfP=-1 pfC=-1 "
            "n=1 P_n1=-1 C_n1=-1 P_n2=-1 C_n2=-1 imm=0 kdec=-1 init=0 split=0 "
            "ge=1 ge_est=223")
        self.assertEqual(event["kind"], "PLAN")
        self.assertEqual(event["ge"], 1)
        self.assertEqual(event["ge_est"], 223)
        old = parse_line(
            "C121_ENGTAB_PLAN pass=1 date=1970-06-01 key=1-2-3-newpair arm=newpair "
            "ap=3 dist=10 paxRawA=50 paxRawB=50 paxA=50 paxB=50 mailRawA=0 mailRawB=0 "
            "eng=7 score=6 P=6 C=1000 dScore=6 dP=6 dC=1000 pfScore=-1 pfP=-1 pfC=-1 "
            "n=1 P_n1=-1 C_n1=-1 P_n2=-1 C_n2=-1 imm=0 kdec=-1 init=0 split=0")
        self.assertNotIn("ge", old)
        rows, unresolved = reconstruct(parse_log_text(
            "C121_ENGTAB_PASS pass=1 date=1970-06-01 engines=3:223\n"
            "C121_ENGTAB_PLAN pass=1 date=1970-06-01 key=1-2-3-newpair arm=newpair "
            "ap=3 dist=10 paxRawA=50 paxRawB=50 paxA=50 paxB=50 mailRawA=0 mailRawB=0 "
            "eng=7 score=6 P=6 C=1000 dScore=6 dP=6 dC=1000 pfScore=-1 pfP=-1 pfC=-1 "
            "n=1 P_n1=-1 C_n1=-1 P_n2=-1 C_n2=-1 imm=0 kdec=-1 init=0 split=0\n"
            "C121_ENGTAB_PLAN pass=1 date=1970-06-01 key=4-5-3-newpair arm=newpair "
            "ap=3 dist=20 paxRawA=40 paxRawB=40 paxA=40 paxB=40 mailRawA=0 mailRawB=0 "
            "eng=223 score=8 P=8 C=1000 dScore=8 dP=8 dC=1000 pfScore=-1 pfP=-1 pfC=-1 "
            "n=1 P_n1=-1 C_n1=-1 P_n2=-1 C_n2=-1 imm=0 kdec=-1 init=0 split=0 "
            "ge=1 ge_est=223\n"
        ), seed=42, game=0)
        self.assertEqual(unresolved, 0)
        self.assertEqual(rows[0]["ge"], 0)
        self.assertEqual(rows[0]["ge_est"], -1)
        self.assertEqual(rows[0]["engines_rows"], [])
        self.assertEqual(rows[1]["ge"], 1)
        self.assertEqual(rows[1]["ge_est"], 223)
        self.assertEqual(rows[1]["engines_rows"], [])

if __name__ == "__main__":
    unittest.main()
