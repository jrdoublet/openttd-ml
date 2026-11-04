"""V190-FIX: independent freight tracks and immutable historical loop behavior."""
import hashlib
from pathlib import Path
import unittest


SOURCE = (Path(__file__).resolve().parents[1] / "ai" / "OpexAI" / "builder_rail.nut").read_text(encoding="utf-8")


def body(name):
    start = SOURCE.index("function " + name + "(")
    brace = SOURCE.index("{", start)
    depth = 0
    for i in range(brace, len(SOURCE)):
        if SOURCE[i] == "{":
            depth += 1
        elif SOURCE[i] == "}":
            depth -= 1
            if not depth:
                return SOURCE[start:i + 1]
    raise AssertionError("unterminated " + name)


class V190FixContracts(unittest.TestCase):
    def test_new_freight_double_is_two_disjoint_tracks_with_own_orders(self):
        verifier = body("OpexV190VerifyIndependentDouble")
        execute = body("OpexV190ExecuteRailPlan")
        self.assertIn("foreach (tile in line.tiles2) if (tile in firstTiles) return false;", verifier)
        self.assertIn("depot1 == depot2", verifier)
        self.assertIn("if (depot1 in secondTiles) return false;", verifier)
        self.assertIn("if (tile in firstPlatformTiles) return false;", verifier)
        self.assertEqual(verifier.count("OpexV190VerifyPrimaryTrackIntact("), 2)
        self.assertIn("OpexV190VerifyIndependentDouble(loopLine, depot, depot2)", execute)
        self.assertIn("OpexV233LIs(candidate)", execute)
        self.assertIn('result.v190Independent <- true', execute)
        self.assertIn('result.v181Loop <- !("v190Independent" in result)', execute)
        self.assertLess(execute.index('OpexV190VerifyIndependentDouble(loopLine, depot, depot2)'),
                        execute.index('foreach (train in trains.vehicles)'))

    def test_extra_clones_forbidden_on_isolated_tracks(self):
        task = (Path(__file__).resolve().parents[1] / "ai" / "OpexAI" / "task_rail.nut").read_text(encoding="utf-8")
        self.assertIn('v190Independent = ("v190Independent" in result)', task)
        self.assertIn('if (("v190Independent" in line) && line.v190Independent) continue;', task)
        self.assertLess(task.index('if (("v190Independent" in line) && line.v190Independent) continue;'),
                        task.index('OpexConvertDoubleTrackToLoop(line);'))

    def test_historical_signal_helper_is_not_changed_by_v190_fix(self):
        helper = body("OpexV181BuildOneWaySignal")
        self.assertNotIn("V190_RAIL_DOUBLE_BUILD", helper)
        self.assertIn("AIRail.BuildSignal(tile, front, AIRail.SIGNALTYPE_PBS)) return 1;", helper)

    def test_v233_loop_remains_legacy_and_v190_not_converted(self):
        loop = body("OpexConvertDoubleTrackToLoop")
        self.assertNotIn("V190_SIGNAL", loop)
        self.assertIn("AIOrder.ShareOrders(otherTrain, firstTrain)", loop)
        self.assertIn('OpexDecide("RAIL_LOOP", "action=convert', loop)
        execute = body("OpexV190ExecuteRailPlan")
        self.assertIn("? OpexConvertDoubleTrackToLoop(loopLine, loopDiag)", execute)
        self.assertIn(": OpexV190VerifyIndependentDouble(loopLine, depot, depot2)", execute)

    def test_off_projection_is_strict_and_preserves_old_code(self):
        from v190_fix_legacy import off_source
        from test_rail_search_prio_20261103 import FIXTURE as search_prio_fixture, off_config_bytes
        from test_rail_search_prio_source_off import off_search_prio_source
        # Les trois insertions de configuration opt-in sont retirees avant
        # toute comparaison historique V190 : aucune empreinte n'est rebasee.
        for name in ("info.nut", "globals_pre.nut", "settings.nut"):
            with self.subTest(name=name):
                config = (Path(__file__).resolve().parents[1] / "ai" / "OpexAI" / name).read_bytes()
                projected_config = off_config_bytes(name, config)
                self.assertEqual(hashlib.sha256(projected_config).hexdigest(),
                                 search_prio_fixture["baseline_sha256"][name])
        task = (Path(__file__).resolve().parents[1] / "ai" / "OpexAI" / "task_rail.nut").read_text(encoding="utf-8")
        projected = off_source("task_rail.nut", off_search_prio_source("task_rail.nut", task))
        self.assertNotIn("v190Independent", projected)
        self.assertNotIn("RAIL_SEARCH_PRIO", projected)
        self.assertEqual(off_source("task_rail.nut", projected), projected)
        with self.assertRaises(AssertionError):
            off_source("task_rail.nut", task.replace("UneRame", "X").replace(
                "Un clone supplementaire", "Plusieurs clones supplementaires"))


if __name__ == "__main__":
    unittest.main()
