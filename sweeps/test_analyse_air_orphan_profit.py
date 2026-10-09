"""Contrats indépendants du moteur : les profits YTD ne sont pas des cashflows."""
from contextlib import redirect_stdout
from datetime import date
import io
import json
from pathlib import Path
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).parent))
from analyse_air_orphan_profit import aidate, analyze, main


def event_date(day):
    return aidate(date.fromisoformat(day))


def logs(build="1972-10-06", other_pair=False, missing_c121=False):
    source = event_date("1972-08-01")
    when = event_date(build)
    rows = [
        ("AIR_ORPHAN_RETAIN date=" + str(source) +
         " anchor=300 station=11 town=10 pair=air|300|900 reason=BFAIL "
         "cost_a=17500 cost_b=200 total=17700 reuse_a=0 reuse_b=0"),
        ("AIR_HUB_REUSE date=" + str(when) +
         " line=18 anchor=300 station=11 side=A prior_line_refs=0 "
         "src_town=10 dst_town=20 reuse_a=1 reuse_b=0"),
    ]
    if not missing_c121:
        rows.append("C121_BUILD line=18 station_id_a=11 station_id_b=22 "
                    "town_a=10 town_b=20 actual_profit=80000")
    if other_pair:
        rows.append("C121_BUILD line=19 station_id_a=11 station_id_b=33 "
                    "town_a=10 town_b=30 actual_profit=50000")
    return "\n".join(rows) + "\n"


def physical_line(station_a=11, station_b=22, towns=(11, 21),
                  vehicles=((7, 1000, 0),), mode="air"):
    ids = sorted([station_a, station_b])
    return {
        "line_key_local": f"{mode}|{ids[0]},{ids[1]}",
        "mode": mode, "station_ids": ids, "town_ids": sorted(towns),
        "ordered_station_ids": [station_a, station_b],
        "ordered_town_ids": list(towns),
        "vehicles": len(vehicles),
        "unitnumbers": [vid + 100 for vid, _, _ in vehicles],
        "vehicle_financials": [
            {"vehicle_id": vid, "profit_this_year_gbp": current,
             "profit_last_year_gbp": previous, "vehicle_value": 25000}
            for vid, current, previous in vehicles
        ],
    }


def snapshot(day, lines=None, seed=1234, arm="OpexAI", policy="reference",
             ok=True, unresolved=None):
    return {
        "duel_policy_id": policy, "arm": arm, "seed": seed, "repeat": 0,
        "date": day, "year": int(day[:4]),
        "ok": ok, "lines": lines if lines is not None else [],
        "unresolved_vehicles": unresolved if unresolved is not None else [],
    }


class AirOrphanProfitTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.engine = self.root / "engine"
        self.engine.mkdir()
        self.log = self.engine / "reference_seed1234_r0.log"
        self.log.write_text(logs(), encoding="utf-8")
        self.result = self.root / "result.json"

    def save(self, snapshots):
        data = {
            "campaign_id": "synthetic_r2",
            "line_telemetry": {
                "schema_version": 1,
                "scope": "monthly savegame post-processing; no NoAI behavior change",
                "snapshots": snapshots,
            },
        }
        self.result.write_text(json.dumps(data), encoding="utf-8")
        return analyze(self.result, [self.log])

    def test_exact_pair_does_not_guess_stnn_town_codec_and_year_reset(self):
        snapshots = [
            snapshot("1972-10-01"),  # avant la construction : jamais une base
            snapshot("1972-11-01", [physical_line(vehicles=((7, 1000, 0),))]),
            snapshot("1972-12-01", [
                physical_line(vehicles=((7, 1600, 0),)),
                # Même aéroport dans une AUTRE ligne : reste indépendant.
                physical_line(11, 33, (11, 31), ((9, 1000, 0),)),
            ]),
            snapshot("1973-01-01", [physical_line(vehicles=((7, 100, 1700),))]),
            snapshot("1973-02-01", [physical_line(vehicles=((7, 300, 1700),))]),
        ]
        report = self.save(snapshots)
        case = report["lines"][0]
        self.assertEqual(case["match_status"], "matched_c121_physical")
        self.assertEqual(case["physical_group"], "air|11,22")
        self.assertEqual(case["first_use_line"], 18)
        self.assertEqual(case["observed_checkpoints"], 4)
        self.assertEqual(case["complete_monthly_intervals"], 3)
        self.assertEqual(case["sum_complete_intervals_gbp"], 1000)
        self.assertEqual(case["snapshots"][0]["period"]["status"], "baseline_unknown")
        self.assertEqual(case["snapshots"][1]["period"]["full_group_delta_gbp"], 600)
        self.assertEqual(case["snapshots"][2]["period"]["full_group_delta_gbp"], 200)
        self.assertTrue(case["snapshots"][2]["period"]["calendar_reset"])
        self.assertEqual(case["snapshots"][2]["period"]["method"], "last_year_bridge")
        self.assertEqual(case["snapshots"][0]["vehicles"][0]["unitnumber"], 107)
        self.assertEqual(case["annual_closures"][0]["closed_calendar_year"], 1972)
        self.assertEqual(case["annual_closures"][0]["surviving_vehicle_profit_last_year_gbp"], 1700)
        self.assertFalse(case["annual_closures"][0]["complete_year_profit_proven"])
        self.assertIn("revenu", report["limitations"][3])

    def test_vehicle_added_and_removed_is_partial_even_when_survivor_known(self):
        rows = [
            snapshot("1972-11-01", [physical_line(vehicles=((7, 1000, 0),
                                                            (8, -100, 0)))]),
            snapshot("1972-12-01", [physical_line(vehicles=((7, 1500, 0),
                                                            (9, 200, 0)))]),
            snapshot("1973-01-01", [physical_line(vehicles=((7, 50, 1700),
                                                            (9, 20, 250)))]),
        ]
        case = self.save(rows)["lines"][0]
        self.assertEqual(case["complete_monthly_intervals"], 1)
        self.assertEqual(case["partial_monthly_intervals"], 1)
        partial = case["snapshots"][1]["period"]
        self.assertEqual(partial["removed_vehicle_ids"], [8])
        self.assertEqual(partial["new_vehicle_ids"], [9])
        self.assertEqual(partial["known_continuing_vehicle_delta_gbp"], 500)
        self.assertIsNone(partial["full_group_delta_gbp"])
        self.assertEqual(case["snapshots"][2]["period"]["full_group_delta_gbp"], 320)

    def test_delayed_rollover_between_january_and_february(self):
        rows = [
            snapshot("1972-11-01", [physical_line(vehicles=((7, 1000, 0),))]),
            snapshot("1972-12-01", [physical_line(vehicles=((7, 1500, 0),))]),
            snapshot("1973-01-01", [physical_line(vehicles=((7, 2000, 0),))]),
            snapshot("1973-02-01", [physical_line(vehicles=((7, 250, 2300),))]),
        ]
        case = self.save(rows)["lines"][0]
        self.assertFalse(case["snapshots"][2]["period"]["calendar_reset"])
        self.assertEqual(case["snapshots"][2]["period"]["full_group_delta_gbp"], 500)
        self.assertTrue(case["snapshots"][3]["period"]["calendar_reset"])
        self.assertEqual(case["snapshots"][3]["period"]["full_group_delta_gbp"], 550)
        self.assertEqual(case["annual_closures"][0]["closed_calendar_year"], 1972)
        self.assertEqual(case["annual_closures"][0]["checkpoint"], "1973-02-01")

    def test_unknown_rollover_at_calendar_boundary_is_not_profit(self):
        rows = [
            snapshot("1972-12-01", [physical_line(vehicles=((7, 1000, 0),))]),
            snapshot("1973-01-01", [physical_line(vehicles=((7, 50, 0),))]),
        ]
        case = self.save(rows)["lines"][0]
        self.assertTrue(case["snapshots"][1]["period"]["mixed_or_unverifiable_rollover"])
        self.assertIsNone(case["snapshots"][1]["period"]["full_group_delta_gbp"])

    def test_group_missing_does_not_mean_zero_profit_or_bridge_a_gap(self):
        rows = [
            snapshot("1972-11-01", [physical_line(vehicles=((7, 1000, 0),))]),
            snapshot("1972-12-01"),
            snapshot("1973-01-01", [physical_line(vehicles=((7, 100, 1800),))]),
        ]
        case = self.save(rows)["lines"][0]
        self.assertEqual(case["observed_checkpoints"], 2)
        self.assertEqual(case["snapshots"][1]["status"], "group_absent")
        self.assertIsNone(case["snapshots"][1]["line_profit_ytd_gbp"])
        self.assertEqual(case["complete_monthly_intervals"], 0)
        self.assertEqual(case["snapshots"][2]["period"]["status"], "missing_or_invalid_group")
        self.assertIsNone(case["sum_complete_intervals_gbp"])

    def test_unresolved_air_vehicle_invalidates_complete_month(self):
        rows = [
            snapshot("1972-11-01", [physical_line()]),
            snapshot("1972-12-01", [physical_line(vehicles=((7, 1200, 0),))],
                     unresolved=[{"mode": "air", "reason": "unreadable_orders"}]),
        ]
        case = self.save(rows)["lines"][0]
        self.assertEqual(case["snapshots"][1]["period"]["status"], "partial")
        self.assertIsNone(case["snapshots"][1]["period"]["full_group_delta_gbp"])

    def test_same_pair_two_builds_ambiguous(self):
        self.log.write_text(logs() + "C121_BUILD line=19 station_id_a=22 "
                            "station_id_b=11 town_a=20 town_b=10\n",
                            encoding="utf-8")
        case = self.save([snapshot("1972-11-01", [physical_line()])])["lines"][0]
        self.assertEqual(case["match_status"], "ambiguous_shared_station_pair")
        self.assertIsNone(case["physical_group"])

    def test_snapshot_group_before_build_must_not_be_reused_as_new(self):
        case = self.save([
            snapshot("1972-09-01", [physical_line()]),
            snapshot("1972-11-01", [physical_line()]),
        ])["lines"][0]
        self.assertEqual(case["match_status"], "ambiguous_preexisting_group")

    def test_no_snapshot_after_build_is_censored_without_profit(self):
        case = self.save([snapshot("1972-10-01"), snapshot("1972-09-01")])["lines"][0]
        self.assertEqual(case["match_status"], "no_postbuild_snapshot")
        self.assertIsNone(case["sum_complete_intervals_gbp"])

    def test_without_c121_town_id_guess_is_rejected(self):
        self.log.write_text(logs(missing_c121=True), encoding="utf-8")
        case = self.save([
            snapshot("1972-11-01", [physical_line(towns=(11, 21))]),
        ])["lines"][0]
        self.assertEqual(case["match_status"], "unmatched_group")
        self.assertIsNone(case["physical_group"])

    def test_metadata_no_cross_arm_and_duplicate_checkpoint(self):
        case = self.save([
            snapshot("1972-11-01", [physical_line()], policy="variant"),
            snapshot("1972-11-01", [physical_line()], arm="AAAHogEx"),
        ])["lines"][0]
        self.assertEqual(case["match_status"], "no_postbuild_snapshot")
        data = self.save([
            snapshot("1972-11-01", [physical_line()]),
            snapshot("1972-11-01", [physical_line()]),
        ])
        self.assertTrue(any("duplicate_snapshot" in warning for warning in data["warnings"]))
        self.assertEqual(data["lines"][0]["match_status"], "unmatched_group")

    def test_jsonl_fallback_and_cli_stdout(self):
        self.result = self.root / "diagnostic.jsonl"
        samples = [
            {"duel_policy_id": "reference", "run": ["OpexAI", 1234, 0],
             "date": "1972-11-01", "line_telemetry": {
                 "ok": True, "lines": [physical_line()],
                 "unresolved_vehicles": []}},
            {"duel_policy_id": "reference", "run": ["OpexAI", 1234, 0],
             "date": "1972-12-01", "line_telemetry": {
                 "ok": True, "lines": [physical_line(vehicles=((7, 1500, 0),))],
                 "unresolved_vehicles": []}},
        ]
        self.result.write_text("\n".join(json.dumps(x) for x in samples), encoding="utf-8")
        with redirect_stdout(io.StringIO()) as stream:
            self.assertEqual(main(["--results", str(self.result),
                                   "--logs", str(self.engine), "--json", "-"]), 0)
        report = json.loads(stream.getvalue())
        self.assertEqual(report["summary"]["physical_groups_matched"], 1)
        self.assertEqual(report["lines"][0]["sum_complete_intervals_gbp"], 500)

    def test_missing_telemetry_json_raises(self):
        self.result.write_text('{"line_telemetry":null}', encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "snapshots absent"):
            analyze(self.result, [self.log])

    def test_strict_real_build_cost_and_missing_ambiguous_fail_closed(self):
        success = ("AIR_FINANCE_TRY date=1972-10-06 rank=2 "
                   "src_town=10 dst_town=20 new_airports=1 "
                   "outcome=built path=portfolio planned=52000 actual=46321 "
                   "reason=OK line=18")
        failed_same_line = ("AIR_FINANCE_TRY date=1972-10-05 "
                            "src_town=11 dst_town=20 outcome=failed "
                            "reason=BFAIL line=18 actual=290")
        snapshots = [snapshot("1972-11-01", [physical_line()])]
        self.log.write_text(logs() + failed_same_line + "\n" + success + "\n",
                            encoding="utf-8")
        matched = self.save(snapshots)["lines"][0]
        self.assertEqual(matched["new_build_cost_status"], "matched_real_build")
        self.assertEqual(matched["new_build_actual_cost_gbp"], 46321)
        self.assertEqual(matched["historical_orphan_cost_a_gbp"], 17500)
        self.assertEqual(matched["combined_historical_spend_gbp"], 63821)
        # Le modèle C121_BUILD actual_profit=80000 n'entre pas dans ce calcul.
        self.assertNotEqual(matched["combined_historical_spend_gbp"], 80000)
        for suffix, status in [
            ("", "missing_built_try"),
            (success + "\n" + success + "\n", "ambiguous_built_try"),
            (success.replace("actual=46321", "planned_other=46321") + "\n",
             "missing_or_invalid_actual"),
            (success.replace("dst_town=20", "dst_town=99") + "\n",
             "ambiguous_build_metadata"),
        ]:
            with self.subTest(status=status):
                self.log.write_text(logs() + failed_same_line + "\n" + suffix,
                                    encoding="utf-8")
                row = self.save(snapshots)["lines"][0]
                self.assertEqual(row["new_build_cost_status"], status)
                self.assertIsNone(row["new_build_actual_cost_gbp"])
                self.assertIsNone(row["combined_historical_spend_gbp"])


if __name__ == "__main__":
    unittest.main()
