"""CARTO-1 long / RLW04b read-only runtime and reservoir contracts.

No AI executable is involved; a 1024^2 in-game smoke still needs to confirm
the original 8500/2700 opcode admission remains sufficient for this sampler.
"""

from pathlib import Path
import re
import unittest


AI = Path(__file__).resolve().parents[1] / "ai" / "OpexAI"


def read(filename):
    return (AI / filename).read_text(encoding="utf-8")


def function_body(source, name):
    match = re.search(r"\bfunction\s+" + re.escape(name) + r"\([^)]*\)\s*\{", source)
    if not match:
        raise AssertionError(f"Missing function: {name}")
    depth = 0
    for index in range(match.end() - 1, len(source)):
        if source[index] == "{":
            depth += 1
        elif source[index] == "}":
            depth -= 1
            if depth == 0:
                return source[match.end():index]
    raise AssertionError(f"Unclosed function: {name}")


class Carto1LongRLWContracts(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.rlw = read("rail_long_window_enumerator.nut")
        cls.main = read("main.nut")
        cls.profiled = read("probes.nut")

    def test_original_cargo_admission_and_native_source_scan(self):
        rlw = self.rlw
        for expected in (
            "OpexGetEpochRailProfile(catalog, cargo, 256)",
            "256.0 * OpexDaysPerTile(profile.speed.tofloat(), 74.0)",
            "AICargo.GetCargoIncome(cargo, 256, info.fast)",
            "AICargo.GetCargoIncome(cargo, 256, info.slow)",
            "info.ratioPm >= 800",
            "AICargo.CC_PASSENGERS", "AICargo.CC_MAIL", "AICargo.TE_GOODS",
            "AIIndustryList_CargoAccepting(u.cargo)",
            "sinks.Valuate(AIIndustry.GetDistanceManhattanToTile, tile)",
            "sinks.KeepBetweenValue(223, 289)",
            "sinks.Count() > RLW04B_SOURCE_CAP",
            "RLW04B_SOURCE_CAP = 512",
            "RLW04B_RESERVE = 8500",
            "RLW04B_SOURCE_RESERVE = 2700",
            "RLW04B_SLICE_BUDGET = 7000",
            "RLW04B_MAX_SLICES_CALL = 16",
            "if (AIController.GetOpsTillSuspend() < admission) break",
        ):
            with self.subTest(expected=expected):
                self.assertIn(expected, rlw)
        self.assertEqual(rlw.count("OpexRLW04BSource(s, this._catalog)"), 1)

    def test_reservoir_includes_every_admitted_pair_and_has_size_30(self):
        body = function_body(self.rlw, "OpexRLW04BSource")
        self.assertIn("const RLW04B_POOL_CAP = 30;", self.rlw)
        self.assertLess(body.index("s.pairs++"), body.index("if (s.sample.len() < RLW04B_POOL_CAP)"))
        self.assertIn("if (s.sample.len() < RLW04B_POOL_CAP) s.sample.append(pair);", body)
        self.assertIn("OpexRLW04BRandBelow(s, s.pairs)", body)
        self.assertIn("if (slot < RLW04B_POOL_CAP) s.sample[slot] = pair;", body)
        self.assertNotIn("s.stocked", self.rlw)
        self.assertNotIn("stockCursor", self.rlw)
        self.assertEqual(self.rlw.count("s.sample.append("), 1)
        self.assertEqual(self.rlw.count("s.sample[slot] ="), 1)
        step = function_body(self.rlw, "OpexAI::_rlw04bStep")
        self.assertLess(step.index("if (s.completed) return;"), step.index("OpexRLW04BSource"))
        self.assertIn('OpexRLW04BLog(s, "done")', step)
        self.assertIn("s.completed = true;", step)

    def test_private_seed_and_unbiased_random_range(self):
        seed = function_body(self.rlw, "OpexRLW04BGameSeed")
        rng = function_body(self.rlw, "OpexRLW04BRandBelow")
        self.assertIn("AIMap.GetMapSizeX()", seed)
        self.assertIn("AIMap.GetMapSizeY()", seed)
        self.assertIn("catalog.industries.len()", seed)
        self.assertIn("item.tile", seed)
        self.assertIn("item.id", seed)
        self.assertIn("OpexRLW04BNextRandom", seed)
        self.assertIn("local maxValue = 2147483646;", rng)
        self.assertIn("maxValue - (maxValue % count)", rng)
        self.assertIn("if (choice < ceiling) return choice % count;", rng)
        self.assertIn("s.rng = OpexRLW04BNextRandom(s.rng);", rng)
        self.assertNotRegex(self.rlw, r"\b(?:AIBase\.Rand|AIController\.GetSeed|AIBase\.RandRange)\s*\(")
        self.assertIn('" sample_seed=" + s.sampleSeed', self.rlw)
        self.assertIn('" rng_state=" + s.rng', self.rlw)

    def test_bit24_is_off_and_carto_long_is_guarded_in_both_loops(self):
        self.assertIn("RLW04B_SHADOW <- false;", read("globals_pre.nut"))
        self.assertIn("RLW04B_SHADOW = OpexProbeEnabled(16777216);", read("settings.nut"))
        self.assertLess(self.main.index('require("probe_carto1.nut")'),
                        self.main.index('require("probe_carto1_long.nut")'))
        self.assertEqual(self.main.count('require("rail_long_window_enumerator.nut")'), 1)
        for name, body in (("main", function_body(self.main, "OpexAI::Start")),
                           ("profiled", function_body(self.profiled, "OpexAI::_mainLoopProfiled"))):
            with self.subTest(loop=name):
                self.assertEqual(body.count("if (RLW04B_SHADOW) this._rlw04bStep();"), 1)
                self.assertEqual(body.count("if (CARTO1_SHADOW && RLW04B_SHADOW && !CARTO2_SHADOW) OpexCarto1LongStep(this);"), 1)
                # The previous loop's RLW enumerator state is consumed before
                # costly orchestrator/event work; the hook checks s.completed.
                self.assertLess(body.index("while (true)"),
                                body.index("OpexCarto1LongStep(this)"))
                self.assertLess(body.index("OpexCarto1LongStep(this)"),
                                body.index("this._processEvents();"))
                self.assertLess(body.index("OpexCarto1LongStep(this)"),
                                body.index("OpexV307MaybeRun("))
                self.assertLess(body.index("OpexCarto1LongStep(this)"),
                                body.index("this._rlw04bStep()"))
                self.assertLess(body.index("OpexCarto1LongStep(this)"), body.rindex("AIController.Sleep(1)"))

    def test_state_is_recreated_and_not_persisted_or_used_for_construction(self):
        self.assertIn("_rlw04bState = null;", self.main)
        start = function_body(self.main, "OpexAI::Start")
        self.assertIn("this._rlw04bState = null;", start)
        self.assertIn("CARTO1_LONG_STATE = null;", start)
        self.assertNotIn("_rlw04bState", read("persist.nut"))
        for forbidden in ("BuildRail(", "BuildVehicle(", "FindPath(",
                          "OpexV276Publish(", "_projects", "AIBase.RandRange("):
            self.assertNotIn(forbidden, self.rlw)

    def test_long_probe_halts_after_first_tick_crossing(self):
        long_probe = read("probe_carto1_long.nut")
        safety = function_body(long_probe, "OpexCarto1LongUnsafe")
        step = function_body(long_probe, "OpexCarto1LongStep")
        self.assertIn('s.stage = "unsafe";', safety)
        self.assertIn("s.finished = true;", safety)
        self.assertIn('OpexCarto1LongSummary(s, "unsafe")', safety)
        self.assertIn('OpexDecide("CARTO1_LONG_SAFETY"', safety)
        self.assertIn('OpexCarto1LongUnsafe(s, row, "carto_tick_cross")', step)
        self.assertIn('OpexCarto1LongUnsafe(s, row, "astar_setup_tick_cross")', step)
        self.assertIn('OpexCarto1LongUnsafe(s, row, "astar_slice_tick_cross")', step)
        self.assertLess(step.index("s.totalSearchOps += s.searchOps - opsBefore;"),
                        step.index('OpexCarto1LongUnsafe(s, row, "astar_slice_tick_cross")'))
        for forbidden in ("AIRail.BuildRail(", "AIRail.BuildRailStation(",
                          "AIVehicle.BuildVehicle(", "AISign.BuildSign("):
            self.assertNotIn(forbidden, long_probe)


if __name__ == "__main__":
    unittest.main()
