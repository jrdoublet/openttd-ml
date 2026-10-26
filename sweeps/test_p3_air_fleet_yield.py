"""P3 source contracts plus fixed, host-only decision fixtures.

No Squirrel engine or OpenTTD is started here. The fixtures mirror the
preregistered thresholds and the source checks prevent accidental drift.
"""
from pathlib import Path
import re
import unittest

from campaign_freeze import parse_ai_settings
from n75_mc_legacy import historical_bytes, historical_info


ROOT = Path(__file__).resolve().parents[1] / "ai" / "OpexAI"


def source(name):
    return (ROOT / name).read_text(encoding="utf-8")


def body(text, signature):
    start = text.index(signature)
    brace = text.index("{", start)
    depth = 0
    for end in range(brace, len(text)):
        if text[end] == "{":
            depth += 1
        elif text[end] == "}":
            depth -= 1
            if depth == 0:
                return text[start:end + 1]
    raise AssertionError(signature)


def model_veto(windows, *, age_days=760, years_since_growth=2,
               fingerprint="1:42:50;2:42:50;", current_fingerprint=None,
               live=2, marginal_samples=1, last_marginal=1000, price=30000,
               scrapping=False, refleet=False, pending_marginal=False):
    """Independent truth-table for the narrow P3 numeric gate (not a VM)."""
    if (age_days < 730 or years_since_growth not in (2, 3) or live < 2
            or marginal_samples < 1 or pending_marginal or scrapping or refleet
            or current_fingerprint not in (None, fingerprint)
            or len(windows) != 3):
        return None
    previous = None
    for w in windows:
        if (w["days"] < 20 or w["days"] > 35 or w["trips"] < 1
                or w["live"] != live or w["cap"] <= 0
                or (previous is not None and previous != w["start"])
                or w["end"] - w["start"] != w["days"]
                or w["wait_n_a"] < 1 or w["wait_n_b"] < 1
                or w["cap"] != windows[0]["cap"]):
            return None
        previous = w["end"]
    days = sum(w["days"] for w in windows)
    trips = sum(w["trips"] for w in windows)
    trips_a = sum(w["trips_a"] for w in windows)
    trips_b = sum(w["trips_b"] for w in windows)
    seats = sum(w["seats"] for w in windows)
    pax = sum(w["pax"] for w in windows)
    wait_a_n = sum(w["wait_n_a"] for w in windows)
    wait_b_n = sum(w["wait_n_b"] for w in windows)
    if (not 65 <= days <= 105 or trips < 6 or trips_a < 2 or trips_b < 2
            or seats <= 0 or not 0 <= pax <= seats
            or wait_a_n < 3 or wait_b_n < 3):
        return None
    wait_a = sum(w["wait_sum_a"] for w in windows) / wait_a_n
    wait_b = sum(w["wait_sum_b"] for w in windows) / wait_b_n
    annual_per_plane = sum(w["profit"] for w in windows) * 365.25 / days / live
    cap_per_plane = windows[-1]["cap"] / live
    return (pax / seats <= .15 and
            wait_a <= cap_per_plane * .25 and
            wait_b <= cap_per_plane * .25 and
            annual_per_plane <= price * .10 and
            0 < last_marginal < price * .08)


def observed_windows():
    return [
        dict(start=0 + 30 * i, end=30 + 30 * i, days=30, live=2,
             trips=3, trips_a=2 if i == 0 else 1,
             trips_b=1 if i == 0 else 2,
             pax=30, seats=300, cap=100, profit=100,
             wait_n_a=4, wait_n_b=4, wait_sum_a=20, wait_sum_b=20)
        for i in range(3)
    ]


class TestP3AirFleetYield(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.info = source("info.nut")
        cls.settings = source("settings.nut")
        cls.globals_pre = source("globals_pre.nut")
        cls.probes = source("probes.nut")
        cls.projects = source("projects_builders.nut")
        cls.execute = source("task_projects.nut")
        cls.air = source("task_air.nut")

    def test_setting_0_1_2_and_four_defaults_exactly_one_read(self):
        settings = parse_ai_settings(ROOT / "info.nut")
        self.assertIn("air_fleet_yield_rightsize", settings)
        decl = re.search(
            r'AddSetting\(\{ name = "air_fleet_yield_rightsize",(.*?)\}\);',
            self.info, re.S
        ).group(1)
        self.assertIn("min_value = 0, max_value = 2", decl)
        for profile in ("easy", "medium", "hard", "custom"):
            self.assertRegex(decl, profile + r"_value = 0\b")
        self.assertEqual(self.settings.count('GetSetting("air_fleet_yield_rightsize")'), 1)
        self.assertIn("P3_AIR_FLEET_YIELD <- 0;", self.globals_pre)
        self.assertIn("P3_AIR_FLEET_WINDOWS <- {};", self.globals_pre)
        self.assertIn("P3_AIR_FLEET_WINDOWS = {};", self.settings)
        # P1/P2, sondes FP1/V286, C75/DIST et trois MULTI-1 opt-in, hors historique P3.
        self.assertEqual(self.info.count("AddSetting("), 73)  # MULTI-1 ROAD SHADOW
        self.assertEqual(historical_info(self.info).count("AddSetting("), 58)

    def test_off_branch_cannot_sample_scan_or_veto(self):
        self.assertIn("if (P3_AIR_FLEET_YIELD > 0)", self.probes)
        self.assertIn("if (P3_AIR_FLEET_YIELD > 0) OpexP3MatureFlush(line, state);",
                      self.probes)
        self.assertIn("if (P3_AIR_FLEET_YIELD > 0 && have >= 2)", self.projects)
        self.assertIn("if (P3_AIR_FLEET_YIELD == 2 && p3 != null && p3.veto",
                      self.projects)
        self.assertIn("if (P3_AIR_FLEET_YIELD == 2 && liveCount >= 2)", self.execute)
        self.assertIn("if (plan == null && P3_AIR_FLEET_YIELD == 2", self.air)
        self.assertNotIn("P3_AIR_FLEET_YIELD", source("persist.nut"))
        self.assertNotIn("P3_AIR_FLEET_WINDOWS", source("persist.nut"))

    def test_save_load_rebuilds_transient_c117_proof(self):
        """Load keeps durable C121 line scalars, not P3 buckets or a veto."""
        main = source("main.nut")
        persist = source("persist.nut")
        self.assertIn("OpexLoadSettings();", main)
        self.assertIn("C117_AIR_LINE_STATE = {};", self.settings)
        self.assertIn("C117_AIR_VEHICLE_STATE = {};", self.settings)
        self.assertIn("P3_AIR_FLEET_WINDOWS = {};", self.settings)
        self.assertIn("function OpexAI::Load(", persist)
        self.assertIn("function OpexAI::_reconcileAfterLoad(", persist)
        self.assertIn("function OpexSaveProjectLine(line)", persist)
        self.assertIn("local serializableLine = clone line;", persist)
        self.assertNotIn("c121MarginalProfit = true", persist)
        self.assertNotIn("p3Signature", persist)
        self.assertNotIn("P3_AIR_FLEET_WINDOWS", persist)
        # Missing proof after reload is UNKNOWN, not a veto even if low margin.
        self.assertIsNone(model_veto([], last_marginal=100))

    def test_po01d_isolation_rejects_unreviewed_p3_edits(self):
        probes_raw = (ROOT / "probes.nut").read_bytes()
        baseline = historical_bytes("probes.nut", probes_raw)
        self.assertNotIn(b"OpexP3MatureEvidence", baseline)
        altered = probes_raw.replace(b"load <= 0.15", b"load <= 0.25", 1)
        with self.assertRaises(AssertionError):
            historical_bytes("probes.nut", altered)

    def test_c117_lean_flush_and_samples_reuse_existing_observations(self):
        flush = body(self.probes, "function OpexC117FlushLine(")
        step = body(self.probes, "function OpexC117AirThroughputStep(")
        self.assertLess(flush.index("OpexC121FirstLiveObserve(line, state, ageDaysLean);"),
                        flush.index("OpexP3MatureFlush(line, state);"))
        self.assertLess(flush.index("OpexP3MatureFlush(line, state);"),
                        flush.index('OpexSpanAgg("loop.c117.flush", flushMark)'))
        self.assertLess(step.index("state.samples++;"),
                        step.index("OpexP3MatureSample(line, state, ageDays, live, mixedEngine);"))
        self.assertIn('state.p3Samples == state.samples', self.probes)
        self.assertIn('state.p3Signature != snapshot.signature', self.probes)
        self.assertIn('holder.history.len() > 3', self.probes)
        self.assertIn('holder.history[holder.history.len() - 1].endDate != state.startDate',
                      self.probes)
        self.assertNotIn("OpexC117AirThroughputStep(", body(self.probes, "function OpexP3MatureEvidence("))

    def test_supported_coverage_and_numerical_veto_are_fixed(self):
        verdict = body(self.probes, "function OpexP3MatureEvidence(")
        for expression in (
            'holder.history.len() != 3', 'today - line.buildDate < 730',
            'sinceGrowth < 2 || sinceGrowth > 3',
            'trips < 6 || tripsA < 2 || tripsB < 2',
            'seats <= 0 || pax < 0 || pax > seats',
            'cap <= 0', 'fleet.signature != holder.signature',
            'load <= 0.15', 'waitingA <= perPlaneCap * 0.25',
            'waitingB <= perPlaneCap * 0.25',
            'annualProfitPerPlane <= planePrice.tofloat() * 0.10',
            'lastMarginal > 0 && lastMarginal < planePrice.tofloat() * 0.08',
        ):
            self.assertIn(expression, verdict)
        self.assertNotIn("GetCargoLoad", verdict)

    def test_shadow_no_decision_and_execute_guards_before_purchase(self):
        make = body(self.projects, "function OpexProjectFromFleet(")
        execute = body(self.execute, "function OpexAI::_tryBuildFleetProject(")
        self.assertIn('OpexDecide("P3_FLEET_YIELD"', make)
        self.assertLess(make.index("OpexV161PerPlaneProfit"),
                        make.index("OpexP3MatureEvidence"))
        self.assertIn("P3_AIR_FLEET_YIELD == 2 && p3 != null && p3.veto", make)
        self.assertIn('!(("p3EngineUpgrade" in entry) && entry.p3EngineUpgrade)', make)
        self.assertLess(execute.index('liveCount != entry.baseVehicles'),
                        execute.index("OpexP3MatureEvidence"))
        self.assertLess(execute.index("OpexP3MatureEvidence"),
                        execute.index("local grown = OpexAirAddPlane"))
        self.assertIn('reason = "p3_low_yield"', execute)
        self.assertIn("OpexP3HasEngineUpgrade(line, this._catalog)", execute)
        self.assertIn("OpexP3HasEngineUpgrade(line, this._catalog)", self.air)

    def test_strong_combination_can_veto(self):
        self.assertIs(model_veto(observed_windows()), True)

    def test_uncertain_windows_never_veto(self):
        cases = [
            ({"age_days": 700}, None),
            ({"years_since_growth": 4}, None),
            ({"marginal_samples": 0}, None),
            ({"pending_marginal": True}, None),
            ({"scrapping": True}, None),
            ({"refleet": True}, None),
            ({"current_fingerprint": "renewed-v252"}, None),
            ({"live": 1}, None),
        ]
        for opts, expected in cases:
            with self.subTest(opts=opts):
                self.assertIs(model_veto(observed_windows(), **opts), expected)

    def test_incomplete_real_trips_seats_and_discontinuous_windows_fail_open(self):
        windows = observed_windows()
        for w in windows:
            w["trips_a"] = 0
        self.assertIsNone(model_veto(windows))
        windows = observed_windows()
        for w in windows:
            w["seats"] = 0
        self.assertIsNone(model_veto(windows))
        windows = observed_windows()
        windows[1]["start"] += 1
        self.assertIsNone(model_veto(windows))
        windows = observed_windows()
        windows[1]["live"] = 3
        self.assertIsNone(model_veto(windows))

    def test_single_corroborating_signal_cannot_veto(self):
        for field, value in (
            ("pax", 90), ("wait_sum_a", 300), ("wait_sum_b", 300),
            ("profit", 5000)
        ):
            windows = observed_windows()
            windows[1][field] = value
            with self.subTest(field=field):
                self.assertIs(model_veto(windows), False)
        self.assertIs(model_veto(observed_windows(), last_marginal=4000), False)
        self.assertIs(model_veto(observed_windows(), last_marginal=-2), False)


if __name__ == "__main__":
    unittest.main()
