"""Passive probe contract and engine-log fixture; no OpenTTD execution."""
from pathlib import Path
import re
import tempfile
import unittest

from analyze_rva_cycle import analyze
from summarize_rva_cycle import summarize

ROOT = Path(__file__).resolve().parents[1]
AI = ROOT / "ai/OpexAI"
FIXTURE = (ROOT / "sweeps/fixtures/rva_cycle.log").read_text(encoding="utf-8")


def read(name):
    return (AI / name).read_text(encoding="utf-8")


class ProbeContract(unittest.TestCase):
    def test_guard_and_default(self):
        self.assertIn("RVA_CYCLE_PROBE <- false;", read("globals_pre.nut"))
        self.assertIn("RVA_CYCLE_PROBE = (probes & 256) != 0;", read("settings.nut"))
        self.assertIn("if ((probes & 1) != 0) probes = probes | 254;", read("settings.nut"))
        self.assertIn("if (RVA_CYCLE_PROBE) OpexRvaCycleStep(this._lines);", read("scheduler.nut"))
        rail = read("task_rail.nut")
        site = rail.index("if (RVA_CYCLE_PROBE) OpexRvaCycleModel(")
        self.assertGreater(site, rail.rfind("if (DECISION_LOG)", 0, site))
        self.assertIn("if (result.ok)", rail[rail.rfind("if (DECISION_LOG)", 0, site):site])
        info = read("info.nut")
        block = info.split('name = "probes",')[1].split("});")[0]
        for difficulty in ("easy", "medium", "hard", "custom"):
            self.assertRegex(block, rf"{difficulty}_value\s*=\s*2")
        self.assertLessEqual(info.count("AddSetting("), 80)  # plafond commun de test_v246 (19/10)
        self.assertIn('require("probe_rva_cycle.nut");', read("main.nut"))

    def test_only_read_only_api_calls(self):
        calls = set(re.findall(r"\b(AI\w+\.\w+)\(", read("probe_rva_cycle.nut")))
        allowed = {"AIStation.GetStationID", "AIDate.GetCurrentDate", "AIVehicle.IsValidVehicle",
                   "AIVehicle.GetLocation", "AIVehicle.GetState", "AIRail.IsRailStationTile",
                   "AIVehicle.IsInDepot", "AIVehicle.GetNumWagons", "AICargo.IsValidCargo",
                   "AIVehicle.GetEngineType", "AIVehicle.GetAge", "AIVehicle.GetLength",
                   "AIVehicle.GetWagonEngineType", "AIVehicle.GetCapacity", "AIVehicle.GetCargoLoad",
                   "AICargo.HasCargoClass", "AIOrder.GetOrderDestination",
                   "AIController.GetTick", "AIController.GetOpsTillSuspend",
                   "AIGameSettings.IsValid", "AIGameSettings.GetValue", "AIRail.GetRailType"}
        self.assertLessEqual(calls, allowed)
        source = read("probe_rva_cycle.nut")
        self.assertNotRegex(source, r"\b(?:foreach|while|for)\s*\(")
        self.assertNotIn("AIVehicleList", source)
        self.assertNotRegex(source, r"line\.\w+\s*(?:=|<-)\s*[^=]")
        for token in ("C67_SLACK_MIN", "work.peakOps + C67_SLACK_RESERVE", "OpexOpsMeasureEnd(mark)"):
            self.assertIn(token, source)
        # Results cannot be consumed by decisions or persistence.
        for path in AI.glob("*.nut"):
            if path.name != "probe_rva_cycle.nut":
                self.assertNotIn("RVA_CYCLE_STATE", path.read_text(encoding="utf-8"))

    def test_units_and_no_reserved_identifiers(self):
        source = read("probe_rva_cycle.nut")
        for token in ("model_ticks_day=74", "model_days_month=30", "length_16tile=", "ops_prefix=", "previous_total="):
            self.assertIn(token, source)
        self.assertNotRegex(source, r"\blocal\s+(clone|base|parent)\b")
        self.assertNotIn("function(", source)  # no implicit closure captures


class Reader(unittest.TestCase):
    def run_log(self, text=FIXTURE):
        return analyze(text.splitlines())

    def test_rotation_units_and_secondary(self):
        result = self.run_log()
        self.assertEqual(result["samples"], 8)
        row, = result["cycles"]
        self.assertEqual(row["cycle_ticks"], [370, 518])
        self.assertEqual(row["outbound_ticks"], [0, 148])
        self.assertEqual(row["dwell_b_ticks"], [74, 222])
        self.assertEqual(row["composition"], {0: 5, 1: 8})
        self.assertEqual(row["residuals"]["model_dwell_per_leg_days"], 1)
        self.assertEqual(row["residuals"]["cycle_delta_model_days"], [0, 4])
        primary, mail = row["residuals"]["cargo"]
        self.assertEqual(primary["capacity_rate"], [80 * 30 / 8, 80 * 30 / 4])
        self.assertEqual(mail["model_capacity_rate"], 300)
        self.assertIsNone(mail["delivered_rate"])
        self.assertEqual(row["dwell_cause"], "unknown")
        self.assertEqual(result["cost"]["previous_total_ops"], [790])
        # Commissioning may occur later than the frozen-model log due to opcodes.
        self.assertIsNotNone(self.run_log(FIXTURE.replace("build_date=100", "build_date=101"))["cycles"][0]["residuals"])
        rows = FIXTURE.splitlines()
        before_begin = "\n".join([rows[1], rows[0]] + rows[2:])
        self.assertIsNotNone(self.run_log(before_begin)["cycles"][0]["residuals"])

    def test_dates_are_independent_of_controller_tick_rate(self):
        scaled = re.sub(r"tick=(\d+)", lambda m: "tick=" + str(int(m[1]) * 4), FIXTURE)
        original = self.run_log()["cycles"][0]
        changed = self.run_log(scaled)["cycles"][0]
        self.assertEqual(original["residuals"], changed["residuals"])
        self.assertEqual(original["cycle_days"], [4, 8])
        self.assertIsNone(self.run_log(re.sub(r" date=\d+", "", FIXTURE))["cycles"][0]["residuals"])
        rollover = FIXTURE.replace("date=107", "date=107 date_end=109")
        self.assertEqual(self.run_log(rollover)["cycles"][0]["cycle_days"], [4, 10])
        backwards = FIXTURE.replace("date=104", "date=99")
        self.assertEqual(self.run_log(backwards)["cycles"], [])
        invalid_end = FIXTURE.replace("date=107", "date=107 date_end=106")
        self.assertIsNone(self.run_log(invalid_end)["cycles"][0]["residuals"])

    def test_summary_keeps_games_separate_and_hashes_sources(self):
        with tempfile.TemporaryDirectory() as tmp:
            paths = [Path(tmp) / name for name in ("seed42.log", "seed7.log")]
            for path in paths:
                path.write_text(FIXTURE, encoding="utf-8")
            result = summarize(paths)
            self.assertEqual(result["summary"]["cycles"], 2)
            self.assertEqual(result["summary"]["ratio_median"], 1.5)
            self.assertEqual(len(result["sources"][0]["sha256"]), 64)
            self.assertEqual({r["source"] for r in result["cycles"]}, {p.name for p in paths})

    def test_empty_and_truncated_never_zero(self):
        result = self.run_log("")
        self.assertEqual(result["coverage"], "not_covered")
        self.assertEqual(result["cycles"], [])
        result = self.run_log("\n".join(FIXTURE.splitlines()[:6]))
        self.assertEqual(result["cycles"], [])
        self.assertEqual(result["missing"][-1]["reason"], "end_of_log")

    def test_skipped_station_and_depot(self):
        for phase in ("A", "D", "X"):
            text = FIXTURE.replace("phase=B", f"phase={phase}")
            result = self.run_log(text)
            self.assertEqual(result["cycles"], [])
            self.assertIn("missing_transition_or_detour", [r["reason"] for r in result["missing"]])

    def test_load_reset_vehicle_lost_and_refit(self):
        rows = FIXTURE.splitlines()
        variants = [rows[:5] + [rows[0]] + rows[5:],
                    rows[:5] + ["OPEX RVA_LOST line=7 vehicle=19"] + rows[5:],
                    rows[:5] + [r.replace("cap=40", "cap=50") for r in rows[5:]]]
        for text in variants:
            self.assertEqual(self.run_log("\n".join(text))["cycles"], [])

    def test_unknown_clock_model_or_mail(self):
        for text in (FIXTURE.replace("timekeeping=0", "timekeeping=1"),
                     "\n".join(r for r in FIXTURE.splitlines() if " RVA_MODEL " not in r)):
            self.assertIsNone(self.run_log(text)["cycles"][0]["residuals"])
        text = FIXTURE.replace("cap2=20", "cap2=na").replace("load2=10", "load2=na")
        self.assertEqual(len(self.run_log(text)["cycles"][0]["residuals"]["cargo"]), 1)

    def test_bad_clock_or_sample(self):
        for text in (FIXTURE.replace("tick=296", "tick=74"),
                     FIXTURE.replace("tick=296", "tick=na")):
            self.assertEqual(self.run_log(text)["cycles"], [])

    def test_order_change_without_observed_station(self):
        rows = FIXTURE.replace("phase=R", "phase=R order_tile=22").splitlines()
        extra = rows[3].replace("tick=74", "tick=100").replace("order_tile=22", "order_tile=11")
        result = self.run_log("\n".join(rows[:4] + [extra] + rows[4:]))
        self.assertEqual(result["cycles"], [])
        self.assertIn("order_changed_between_samples", [r["reason"] for r in result["missing"]])

    def test_sample_crossing_tick_widens_bounds(self):
        text = FIXTURE.replace("tick=518", "tick=518 tick_end=592")
        self.assertEqual(self.run_log(text)["cycles"][0]["cycle_ticks"], [370, 592])

    def test_partial_identity_is_not_covered(self):
        result = self.run_log("OPEX RVA_SAMPLE tick=12\nOPEX RVA_SAMPLE line=1 vehicle=2 tick=na")
        self.assertEqual(result["cycles"], [])
        self.assertEqual(result["missing"][0]["reason"], "incomplete_identity")

    def test_probe_cost_and_exposure_frames(self):
        text = FIXTURE + "\nOPEX RVA_COST seq=9 completed_ops=1400 ops_prefix=450 model_completed_ops=500 calls=9 skipped=2\n"
        text += "OPEX RVA_SWEEP sweep=1 lines=9 eligible=1 sampled=1 lost=0\n"
        result = self.run_log(text)
        self.assertEqual(result["cost"]["frames"][-1]["skipped"], 2)
        self.assertEqual(result["sweeps"][0]["eligible"], 1)
        self.assertEqual(result["cost"]["session_totals"][0]["ops_per_observation"], 2350 / 8)


if __name__ == "__main__":
    unittest.main()
