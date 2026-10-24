"""Contrats source AIR load opt-in. Ne compilent pas Squirrel et ne jouent pas.

Le suivi C117 existant fournit un maximum en mouvement par trajet, pas une
moyenne des photos en vol. Les hashes hors gardes verrouillent le chemin OFF.
"""
import hashlib
import re
import unittest
from pathlib import Path

from test_b5_rail_persistence import function_body

AI = Path(__file__).resolve().parents[1] / "ai" / "OpexAI"


def read(name):
    return (AI / name).read_text(encoding="utf-8")


def body(name, signature):
    return function_body(read(name), "function " + signature)


class AirLoadGuard(unittest.TestCase):
    def test_off_paths_match_origin_master_after_removing_only_opt_in_hooks(self):
        # origin/master eec5db81. Exact old bodies after neutralising the new
        # short-circuited hooks; this is not a claim of identical opcode timing.
        for name, signature, digest in (
            ("task_air.nut", "OpexAI::_resizeAirFleets(",
             "19797f4999777ff45fd358e4a6f93bf2354e2a8a2a36fb5180620918bc27abda"),
            ("task_projects.nut", "OpexAI::_tryBuildFleetProject(",
             "a107491c46fe7ee575913b00f8a478c79619f9f0bb2d653766368dbed0b0353c"),
            ("probes.nut", "OpexC117AirThroughputStep(",
             "f666e14183ed62cc530334790502480b7b08be53296b77a510dbdfdf5f57511c"),
        ):
            with self.subTest(name=name):
                code = body(name, signature)
                code = code.replace("  /* A listed fleet project can outlive its load observation: revalidate at purchase. */\n", "")
                code = code.replace("          if (AIR_LOAD_MIN_PCT > 0) vehicleState.airLoadInvalid <- true;\n", "")
                match = re.search(r"(?m)^ +if \(AIR_LOAD_MIN_PCT > 0[^\n]*\{", code)
                self.assertIsNotNone(match)
                inner = function_body(code[match.start():], "if (")
                end = code.index("{", match.start()) + len(inner) + 2
                self.assertEqual(code[end], "\n")
                code = code[:match.start()] + code[end + 1:]
                self.assertEqual(hashlib.sha256(code.encode()).hexdigest(), digest)

    def test_setting_bounds_step_four_defaults_and_single_read(self):
        setting = re.search(r'AddSetting\(\{ name = "air_load_min_pct",(.*?)\}\);',
                            read("info.nut"), re.S).group(1)
        for level in ("easy", "medium", "hard", "custom"):
            self.assertIn(level + "_value = 0", setting)
        self.assertIn("min_value = 0, max_value = 100, step_size = 5", setting)
        self.assertIn("AIR_LOAD_MIN_PCT <- 0;", read("globals_pre.nut"))
        self.assertEqual(read("settings.nut").count('GetSetting("air_load_min_pct")'), 1)

    def test_both_growth_paths_guarded_before_purchase(self):
        for name, signature in (("task_air.nut", "OpexAI::_resizeAirFleets("),
                                ("task_projects.nut", "OpexAI::_tryBuildFleetProject(")):
            code = body(name, signature)
            guard = code.index("if (AIR_LOAD_MIN_PCT > 0 && OpexAirLoadBlocksGrowth(line))")
            self.assertLess(guard, code.index("local need ="))
            self.assertIn('OpexAirFleetRefusal(line, year, "F");', code[guard:])
            self.assertIn('OpexC73RecordRejection("fleet", "low_load_factor", 1)', code[guard:])
        code = body("task_air.nut", "OpexAI::_resizeAirFleets(")
        # Garde commune a l'execution et au plan a blanc, sans condition plan != null.
        self.assertIn("if (plan != null && C69_BOTTLENECK_PROBE) OpexC73RecordRejection(\"fleet\", \"low_load_factor\", 1);", code)

    def test_insufficient_unknown_stale_and_non_air_allow_growth(self):
        code = body("task_air.nut", "OpexAirLoadBlocksGrowth(")
        for guard in ('AIR_LOAD_MIN_PCT <= 0', 'line.mode != "air"',
                      '!("airLoad" in line) || line.airLoad.legs.len() < 6',
                      'AIDate.GetCurrentDate() - line.airLoad.date > 180'):
            self.assertIn(guard, code)
            self.assertLess(code.index(guard), code.index("return OpexAirLoadPct"))
        self.assertIn("return OpexAirLoadPct(line) < AIR_LOAD_MIN_PCT;", code)
        self.assertIn('if (!("airLoad" in line) || line.airLoad.legs.len() < 6) return false;', code)
        self.assertIn('if (AIDate.GetCurrentDate() - line.airLoad.date > 180) return false;', code)

    def test_crash_recovery_precedes_guard_and_renewal_is_independent(self):
        code = body("task_air.nut", "OpexAI::_resizeAirFleets(")
        self.assertLess(code.index("OpexAirRefleetCrashedPlane("),
                        code.index("OpexAirLoadBlocksGrowth("))
        self.assertIn('if (("needsRefleet" in line) && line.needsRefleet) return false;',
                      body("task_air.nut", "OpexAirLoadBlocksGrowth("))
        self.assertNotIn("AirLoad", read("task_v252.nut"))
        self.assertNotIn("AIR_LOAD", read("air_fleet.nut"))

    def test_window_bounded_weighted_and_no_array_shift(self):
        code = body("task_air.nut", "OpexAirLoadRecord(")
        for fragment in ("capacity <= 0 || load < 0 || load > capacity", "window.legs.len() == 12",
                         "window.load -= old[0]", "window.capacity -= old[1]",
                         "window.cursor = (window.cursor + 1) % 12", "window.load += load",
                         "window.capacity += capacity", "now - line.airLoad.date > 180"):
            self.assertIn(fragment, code)
        self.assertNotIn(".remove(", code)
        self.assertIn("100.0 * line.airLoad.load / line.airLoad.capacity",
                      body("task_air.nut", "OpexAirLoadPct("))

    def test_record_once_per_transition_excluding_partial_and_invalid_legs(self):
        code = body("probes.nut", "OpexC117AirThroughputStep(")
        record = code.index("OpexAirLoadRecord(")
        same_order = code.index("if (curOrder == vehicleState.order)")
        self.assertIn("continue;", code[same_order:record])
        self.assertIn("if (AIR_LOAD_MIN_PCT > 0) {\n          if (vehicleState.seenTransition && vehicleState.legMoving", code)
        self.assertIn('&& !("airLoadInvalid" in vehicleState)', code[:record])
        self.assertIn("OpexAirLoadRecord(line, vehicleState.legPaxMax, vehicleState.legCap, now)", code)
        self.assertIn("if (AIR_LOAD_MIN_PCT > 0) vehicleState.airLoadInvalid <- true;", code)
        self.assertEqual(code.count("OpexAirLoadRecord("), 1)
        self.assertIn("seenTransition = false", code)
        self.assertIn("AIVehicle.GetState(v) == AIVehicle.VS_RUNNING", code)

    def test_no_new_vehicle_api_calls_or_loop_hooks(self):
        for name in ("main.nut", "probes.nut"):
            self.assertIn("OpexC117AirThroughputStep(this._lines, this._catalog);", read(name))
        for signature in ("OpexAirLoadRecord(", "OpexAirLoadPct(", "OpexAirLoadBlocksGrowth("):
            code = body("task_air.nut", signature)
            self.assertNotIn("AIVehicle.", code)
            self.assertNotIn(".Valuate(", code)
            self.assertNotIn("foreach", code)

    def test_logs_include_count_load_and_refusal_reason(self):
        code = body("task_air.nut", "OpexAirLoadRecord(")
        self.assertIn('if (DECISION_LOG) OpexDecide("AIR_LOAD", "line="', code)
        self.assertIn('" samples=" + window.legs.len()', code)
        self.assertIn('" load_pct=" + OpexAirLoadPct(line)', code)
        refusal = body("task_air.nut", "OpexAirFleetRefusal(")
        self.assertIn('code == "F") reasonStr = "low_load_factor"', refusal)
        self.assertIn('code == "F" ? " load_pct="', refusal)

    def test_integer_window_preserved_and_partial_vehicle_state_rebuilt_on_load(self):
        save = body("persist.nut", "OpexSaveProjectLine(")
        self.assertIn("local serializableLine = clone line;", save)
        self.assertIn('valType != "array" && valType != "table"', save)
        self.assertNotIn("airLoad", read("persist.nut"))  # no skip/drop special case
        self.assertIn('if ("lines" in data) this._pendingLines = data.lines;', read("persist.nut"))
        self.assertIn("liveLines.append(line);", read("persist.nut"))
        self.assertIn("C117_AIR_VEHICLE_STATE <- {};", read("globals_pre.nut"))
        self.assertNotIn("C117_AIR_VEHICLE_STATE", read("persist.nut"))


if __name__ == "__main__":
    unittest.main()
