"""FRONT-PAX-2: contrats statiques et fixture d'une sonde passive.

Le modele de la classification ne compile ni n'execute Squirrel/OpenTTD.
Les assertions statiques rattachent les points d'observation aux boucles reelles.
"""

import json
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]
SOURCE = (ROOT / "ai/OpexAI/air_planning.nut").read_text(encoding="utf-8")
POLICY = (ROOT / "ai/OpexAI/candidates.nut").read_text(encoding="utf-8")
FIXTURE = json.loads((ROOT / "sweeps/fixtures/front_pax2_cases.json").read_text(encoding="utf-8"))
FIELDS = ("seen", "short", "belowMin", "minBlocked", "belowAirMax",
          "belowPlaneMax", "belowConfigMax", "belowWithinLimits",
          "otherBand", "airMax", "bandPass")


def function_body(name):
    begin = SOURCE.index("function " + name + "(")
    brace = SOURCE.index("{", begin)
    depth = 0
    for i in range(brace, len(SOURCE)):
        if SOURCE[i] == "{":
            depth += 1
        elif SOURCE[i] == "}":
            depth -= 1
            if depth == 0:
                return SOURCE[begin:i + 1]
    raise AssertionError("unbalanced function: " + name)


def initial():
    return [{"under20": 0, **{key: [0] * 4 for key in FIELDS}} for _ in range(3)]


def record(counts, item, bounds, config_max):
    """Modele de la bande originale, avec les seuils de constructeur en aval."""
    arm, distance, flight, minimum, band, plane_max = item
    out = counts[arm]
    if distance < 20:
        out["under20"] += 1
        return
    bin_index = next((i for i, limit in enumerate((64, 78, 200)) if distance < limit), 3)
    out["seen"][bin_index] += 1
    if distance < minimum:
        out["short"][bin_index] += 1
        return

    if band == "air_only":
        band_ok = distance > bounds["railMax"]
    elif band == "air_rail":
        band_ok = bounds["railAirOverlapMin"] <= distance <= bounds["railMax"]
    else:
        band_ok = distance >= bounds["airMin"]
    airmax_ok = bounds["airMax"] <= 0 or flight <= bounds["airMax"]
    if distance < bounds["airMin"]:
        out["belowMin"][bin_index] += 1
        if not airmax_ok:
            out["belowAirMax"][bin_index] += 1
        if plane_max > 0 and flight > plane_max:
            out["belowPlaneMax"][bin_index] += 1
        if config_max > 0 and flight > config_max:
            out["belowConfigMax"][bin_index] += 1
        if airmax_ok and (plane_max <= 0 or flight <= plane_max) and (config_max <= 0 or flight <= config_max):
            out["belowWithinLimits"][bin_index] += 1
    if band == "all" and distance < bounds["airMin"]:
        out["minBlocked"][bin_index] += 1
    elif not band_ok:
        out["otherBand"][bin_index] += 1
    elif not airmax_ok:
        out["airMax"][bin_index] += 1
    else:
        out["bandPass"][bin_index] += 1


class FrontPax2Contract(unittest.TestCase):
    def test_fixed_fixture_matches_distance_bins_and_separate_band_reasons(self):
        actual = initial()
        for item in FIXTURE["records"]:
            record(actual, item, FIXTURE["bounds"], FIXTURE["configMax"])
        self.assertEqual(actual, FIXTURE["golden"])
        for arm in actual:
            for i in range(4):
                self.assertEqual(arm["seen"][i], sum(arm[field][i] for field in (
                    "short", "minBlocked", "otherBand", "airMax", "bandPass")))
                self.assertGreaterEqual(arm["belowMin"][i], arm["minBlocked"][i])
                self.assertGreaterEqual(arm["belowMin"][i], arm["belowWithinLimits"][i])

    def test_sliced_accumulation_matches_one_pass_without_deduplicating_pairs(self):
        records = FIXTURE["records"]
        one = initial()
        sliced = initial()
        for item in records:
            record(one, item, FIXTURE["bounds"], FIXTURE["configMax"])
        for fragment in (records[:4], records[4:9], records[9:17], records[17:]):
            for item in fragment:
                record(sliced, item, FIXTURE["bounds"], FIXTURE["configMax"])
        self.assertEqual(sliced, one)

    def test_configured_max_distance_is_independent_of_engine_and_band(self):
        counts = initial()
        bounds = FIXTURE["bounds"]
        record(counts, [0, 78, 230, 32, "air_rail", 250], bounds, 210)
        self.assertEqual(counts[0]["belowMin"][2], 1)
        self.assertEqual(counts[0]["belowConfigMax"][2], 1)
        self.assertEqual(counts[0]["belowPlaneMax"][2], 0)
        self.assertEqual(counts[0]["otherBand"][2], 1)
        self.assertEqual(counts[0]["minBlocked"][2], 0)
        self.assertEqual(counts[0]["belowWithinLimits"][2], 0)

    def test_same_filter_order_and_boundaries_as_production(self):
        self.assertIn("manhattan < b.airMin", POLICY)
        self.assertIn("manhattan <= b.railMax", POLICY)
        self.assertIn("manhattan < b.railAirOverlapMin || manhattan > b.railMax", POLICY)
        self.assertIn("b.airMax > 0 && flightDistance > b.airMax", POLICY)
        observation = function_body("OpexFrontPax2Observe")
        for expected in ("distance < 20", "distance < 64", "distance < 78",
                         "distance < 200", "distance < minDist", "distance < b.airMin",
                         "distance <= b.railMax", "distance < b.railAirOverlapMin",
                         "flightDistance > b.airMax", "flightDistance > planeMax"):
            self.assertIn(expected, observation)
        for forbidden in ("AIMap.", "AITile.", "AIController.", ".Valuate(", "OpexAirPairInBand("):
            self.assertNotIn(forbidden, observation)

    def test_only_three_arms_and_one_bounded_summary_per_completed_scan(self):
        driver = function_body("OpexAirPlans")
        fin = function_body("OpexAirPlansFinalize")
        self.assertIn("if (DECISION_LOG)", driver)
        self.assertIn('"frontPax2" in resumeState', driver)
        self.assertIn("resumeState.frontPax2 <- ctx.fp2;", driver)
        self.assertIn("fp2 = null", driver)
        self.assertIn("year = bounds.year", function_body("OpexFrontPax2Init"))
        self.assertNotIn("OpexFrontPax2Emit", driver)
        self.assertEqual(fin.count("OpexFrontPax2Emit(ctx.fp2"), 1)
        self.assertLess(fin.index("OpexFrontPax2Emit("), fin.index("resumeState.done = true"))
        prepare = function_body("OpexAirPlansPrepare")
        self.assertEqual(prepare.count("OpexFrontPax2Emit(ctx.fp2"), 1)
        self.assertLess(prepare.index("OpexFrontPax2Emit("), prepare.index("resumeState.done = true"))
        emit = function_body("OpexFrontPax2Emit")
        self.assertIn('local names = ["newpair", "hubsite", "hubhub"]', emit)
        self.assertIn("i < 3", emit)
        self.assertEqual(emit.count('OpexDecide("FRONT_PAX2"'), 1)

    def test_instrumentation_stays_on_existing_pair_distances(self):
        for method, arm, call_count in (("OpexAirPlansNewPairs", 0, 1),
                                        ("OpexAirPlansHubToSite", 1, 2),
                                        ("OpexAirPlansHubToHub", 2, 2)):
            body = function_body(method)
            event = f"OpexFrontPax2Observe(ctx.fp2, {arm}, distance,"
            self.assertEqual(body.count(event), call_count)
            self.assertLess(body.index("AIMap.DistanceManhattan("), body.index(event))
            self.assertLess(body.index(event), body.index("OpexAirPairInBand("))
            self.assertIn("if (ctx.fp2 != null)", body)
        self.assertIn("if (ctx.fp2 != null)", function_body("OpexAirPlansFinalize"))


if __name__ == "__main__":
    unittest.main()
