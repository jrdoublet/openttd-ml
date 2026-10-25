"""Synthetic CARTO-2 contract fixtures: no engine or Docker required."""

import contextlib
import gzip
import io
import json
from pathlib import Path
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parent))
from analyze_carto2 import (analyze_sources, analyze_paths, decode_line, main,
                            parse_game, render_markdown, validate_campaign)


def log(tag, when="1974-12-31", **fields):
    return "DEBUG [AI] OPEX " + when + " " + tag + " " + " ".join(
        f"{name}={value}" for name, value in fields.items()) + "\n"


def game(seed=42):
    entries = [log("CARTO2_START", when="1970-01-01", seed=seed, mapx=1024,
                   mapy=1024, source_sha="fixture-sha")]
    # Four separate match classes; equal/longer route quality when both ready.
    arms = [
        (("OK", 1, 120, 3200, 0, 246), ("OK", 1, 80, 2000, 0, 242)),
        (("ABND", 0, 900, 12000, 2, -1), ("OK", 1, 200, 3800, 0, 250)),
        (("OK", 1, 100, 2400, 0, 270), ("DEAD", 0, 750, 10500, 1, -1)),
        (("DEAD", 0, 900, 12500, 2, -1), ("ABND", 0, 820, 11200, 2, -1)),
    ]
    for pair_id, (free, guided) in enumerate(arms):
        key = f"freight:{pair_id}:100:200"
        entries.append(log("CARTO2_PAIR", id=pair_id, key=key,
                           src=100 + pair_id, dst=200 + pair_id, dist=240))
        entries.append(log("CARTO2_COST", id=pair_id, key=key,
                           band_ops=120, line_ops=50, band_ticks=0,
                           line_ticks=0, band_cells=30, line_cells=10))
        for mode, sample in (("free", free), ("guided", guided)):
            outcome, ready, iters, ops, ticks, path_dist = sample
            entries.append(log("CARTO2_SEARCH", id=pair_id, key=key,
                               mode=mode, phase="end", outcome=outcome,
                               iters=iters, ops=ops, ticks=ticks, ready=ready,
                               path_dist=path_dist))
    entries.append(log("CARTO2_SUMMARY", phase="done", pairs=4, year=1974))
    return entries


def sources():
    return [("reference_seed42_r0.log", game(42)),
            ("reference_seed100_r0.log", game(100))]


def harness():
    keys = [42, 100]
    result = {
        "campaign_id": "carto2_fixture", "years": 5, "start_year": 1970,
        "source_bundle_sha256": "fixture-bundle",
        "expected_last_year": 1974, "seeds": keys, "repeats": 1, "map_size": 10,
        "games": [
            {"policy_id": "reference", "seed": seed, "repeat": 0,
             "engine_log_path": f"/work/results/carto2/reference_seed{seed}_r0.log",
             "game_status": "complete", "game_ok": True, "unattributed_errors": [],
             "companies": {"OpexAI": {"horizon_complete": True}}}
            for seed in keys],
    }
    manifest = {
        "campaign_id": "carto2_fixture", "git": {"sha": "fixture-sha"},
        "source_bundle": {"sha256": "fixture-bundle"},
        "execution": {"options": {"script_debug": True,
                                  "docker_image_id": "sha256:fixture"}},
        "configuration": {"years": 5, "starting_year": 1970,
                          "seeds": keys, "repeats": 1, "map_size": 10},
        "games": [{"policy_id": "reference", "seed": seed, "repeat": 0}
                  for seed in keys],
    }
    return result, manifest


def partial_search_game(seed):
    """r2-shaped fixtures: paired 42, no searches 100, free-only 999."""
    events = [log("CARTO2_START", when="1970-1-20",
                  mapx=1024, mapy=1024, start_year=1970, years=5,
                  seed=1791467322),
              log("CARTO2_PAIR", when="1970-2-1", id=0,
                  key=f"freight:1:{seed}:200", src=seed, dst=200,
                  dist=240, source="long")]
    if seed in (42, 100):
        events.append(log("CARTO2_COST", when="1970-7-1", id=0,
                          key=f"freight:1:{seed}:200", source="long",
                          band_ops=120, line_ops=50, band_ticks=0,
                          line_ticks=0, band_cells=30, line_cells=10))
    variants = {
        42: (("free", "1970-11-23", 2, 5197),
             ("guided", "1971-7-2", 4, 6939)),
        100: (),
        999: (("free", "1972-6-23", 442, 862164),),
    }
    for mode, when, iters, ops in variants[seed]:
        events.append(log("CARTO2_SEARCH", when=when, id=0,
                          key=f"freight:1:{seed}:200", source="long",
                          mode=mode, phase="end", outcome="CANCEL",
                          iters=iters, ops=ops, ticks=0, ready=0,
                          path_dist=-1))
    events.append(log("CARTO2_SUMMARY", when="1974-12-1",
                      phase="progress", pairs=1, mapped=int(seed != 999),
                      completed=int(seed == 42), ready=0, year=1974))
    return events


def carto2b_game(seed=42):
    """One line-only map per pair, two V309 full turns, both OK and failures."""
    entries = []
    for entry in game(seed):
        if "CARTO2_COST" in entry:
            entry = entry.replace("band_ops=120", "band_ops=-1")
            entry = entry.replace("band_cells=30", "band_cells=-1")
            entry = entry.replace("CARTO2_COST ", "CARTO2_COST map_mode=line ")
        if "CARTO2_SUMMARY" in entry:
            continue
        entries.append(entry)
    entries.extend([
        log("CARTO2_TURN", when="1971-05-01", phase="full", ops=8800,
            left=1080, date="1971-05-01", year=1971),
        log("CARTO2_TURN", when="1973-06-02", phase="full", ops=9100,
            left=700, date="1973-06-02", year=1973),
        log("CARTO2_SUMMARY", phase="done", pairs=4, mapped=4,
            completed=4, ready=2, year=1974, ticks=0,
            full_turns=2, full_turn_ops=17900, paused_turns=3),
    ])
    return entries


class CARTO2AnalysisTests(unittest.TestCase):
    def test_parser_date_decoration_and_reject_bad_dates(self):
        self.assertEqual(decode_line(log("CARTO2_PAIR", when="1974-2-5", id=1))[0].isoformat(),
                         "1974-02-05")
        self.assertIsNone(decode_line(log("CARTO2_PAIR", when="1974-99-31", id=1)))
        self.assertIsNone(decode_line("CARTO2_PAIR id=0"))
        self.assertIsNone(decode_line(log("ANOTHER_EVENT", id=0)))

    def test_paired_all_outcomes_and_cost_aggregate(self):
        report = analyze_sources(sources())
        policy = report["policies"]["reference"]
        agg = policy["aggregate"]
        self.assertTrue(policy["log_complete"], policy["errors"])
        self.assertFalse(policy["complete"])  # needs manifest and result evidence
        self.assertEqual(agg["pairs"], 8)
        self.assertEqual(agg["classification"], {
            "both_ready": 2, "free_only_ready": 2,
            "guided_only_ready": 2, "neither_ready": 2})
        self.assertEqual((agg["free_ready1974"], agg["guided_ready1974"]), (4, 4))
        self.assertEqual(agg["quality_classification"], {"guided_shorter": 2})
        self.assertEqual(agg["band_ops"]["sum"], 960)
        self.assertEqual(agg["line_ops"]["sum"], 400)
        self.assertEqual(agg["band_extra_ops"]["sum"], 560)
        self.assertEqual(agg["band_cells"]["sum"], 240)
        self.assertEqual(agg["line_cells"]["sum"], 80)
        self.assertEqual(agg["free_ticks_crossed"]["sum"], 8)
        self.assertEqual(agg["guided_ticks_crossed"]["sum"], 6)
        self.assertEqual(agg["saved_ticks"]["sum"], 2)
        self.assertEqual(agg["saved_ops"]["sum"], 5200)
        self.assertEqual(agg["path_distance_delta"]["sum"], -8)
        self.assertIn("fin 1974", render_markdown(report))
        self.assertIn("Ticks traversés libres", render_markdown(report))
        self.assertIn("Δ ops L−G", render_markdown(report, show_pairs=True))
        self.assertIn("Paire", render_markdown(report, show_pairs=True))

    def test_carto2b_line_mode_v309_turns_and_ok_only_comparisons(self):
        report = analyze_sources([("carto2_seed42_r0.log", carto2b_game())])
        policy = report["policies"]["carto2"]
        game_row = policy["games"][0]
        self.assertTrue(game_row["log_complete"], game_row["errors"])
        self.assertEqual(game_row["events"]["CARTO2_TURN"], 2)
        self.assertEqual(game_row["v309_turns"]["observed_full_turns"], 2)
        self.assertEqual(game_row["v309_turns"]["observed_full_turn_ops"]["sum"], 17900)
        self.assertEqual(game_row["v309_turns"]["observed_left"]["sum"], 1780)
        self.assertEqual(game_row["v309_turns"]["reported_full_turns"], 2)
        self.assertEqual(game_row["v309_turns"]["reported_full_turn_ops"], 17900)
        self.assertEqual(game_row["v309_turns"]["reported_paused_turns"], 3)
        self.assertEqual(game_row["v309_turns"]["reported_runtime_ticks"], 0)
        self.assertEqual(policy["v309_turns"]["reported_paused_turns"], 3)
        self.assertEqual(policy["mapped_partial"]["by_map_mode"], {"line": 4})
        self.assertEqual(policy["mapped_partial"]["line_ops"]["sum"], 200)
        self.assertEqual(policy["mapped_partial"]["band_ops"]["n"], 0)
        self.assertEqual(policy["mapped_partial"]["band_cells"]["n"], 0)
        self.assertEqual(policy["mapped_partial"]["extra_ops"]["n"], 0)
        self.assertEqual(policy["aggregate"]["band_extra_ops"]["n"], 0)
        self.assertIsNone(game_row["mapped"][0]["band_ops"])
        self.assertIsNone(game_row["rows"][0]["cost"]["ops_ratio"])
        self.assertEqual(policy["aggregate"]["pairs"], 4)  # all terminal pairs descriptive
        ok = policy["astar_ok_pairs"]
        self.assertEqual(ok["count"], 1)  # FAIL, DEAD and ABND excluded
        self.assertEqual(ok["with_known_distances"], 1)
        self.assertEqual(ok["saved_iters"]["sum"], 40)
        self.assertEqual(ok["saved_ops"]["sum"], 1200)
        self.assertEqual(ok["saved_ticks"]["sum"], 0)
        self.assertEqual(ok["free_path_dist"]["sum"], 246)
        self.assertEqual(ok["guided_path_dist"]["sum"], 242)
        self.assertEqual(ok["path_distance_delta"]["sum"], -4)
        self.assertEqual(ok["quality_classification"], {"guided_shorter": 1})
        self.assertEqual(ok["pairs"][0]["key"], "freight:0:100:200")
        self.assertTrue(game_row["readiness"]["snapshot_on_end_date"])
        self.assertEqual(game_row["ready_at_end_snapshot"], 2)
        self.assertEqual(game_row["readiness"]["cache_ttl_days"], 180)
        md = render_markdown(report, show_pairs=True)
        for phrase in ("V309", "seed42/r0", "17900", "8800", "9100",
                       "Tours en pause", "non mesurée", "A* OK/OK",
                       "246/242", "Distance guidé", "31/12/1974"):
            self.assertIn(phrase, md)
        json_roundtrip = json.loads(json.dumps(report))
        self.assertEqual(json_roundtrip["policies"]["carto2"]["v309_turns"]
                         ["reported_paused_turns"], 3)
        self.assertIsNone(json_roundtrip["policies"]["carto2"]
                          ["games"][0]["mapped"][0]["band_ops"])

    def test_carto2b_cumulative_summary_not_multiplied_and_per_seed(self):
        a = carto2b_game(42)
        a.insert(1, log("CARTO2_SUMMARY", when="1971-06-01", phase="progress",
                        pairs=4, mapped=0, completed=0, ready=0, year=1971,
                        full_turns=1, full_turn_ops=8800, paused_turns=1))
        b = [entry.replace("ops=8800", "ops=8000")
             .replace("full_turn_ops=17900", "full_turn_ops=17100")
             for entry in carto2b_game(100)]
        report = analyze_sources([("carto2_seed42_r0.log", a),
                                  ("carto2_seed100_r0.log", b)])
        policy = report["policies"]["carto2"]
        self.assertTrue(policy["log_complete"], policy["errors"])
        self.assertEqual(policy["v309_turns"]["reported_full_turns"], 4)
        self.assertEqual(policy["v309_turns"]["reported_full_turn_ops"], 35000)
        self.assertEqual(policy["v309_turns"]["reported_paused_turns"], 6)
        self.assertEqual(policy["v309_turns"]["observed_full_turns"], 4)
        self.assertEqual(policy["astar_ok_pairs"]["count"], 2)
        self.assertEqual([g["v309_turns"]["reported_full_turn_ops"]
                          for g in policy["games"]], [17900, 17100])

    def test_carto2b_bad_turn_or_cumulative_summary_fail_closed(self):
        bad_cases = [
            ("ops=8800", "ops=-1", "TURN ops"),
            ("left=1080", "left=10001", "TURN left"),
            ("phase=full ops=8800", "phase=paused ops=8800", "TURN phase"),
            ("date=1971-05-01", "date=1971-05-02", "TURN date"),
            ("year=1971", "year=1972", "TURN year"),
            ("full_turn_ops=17900", "full_turn_ops=17000", "SUMMARY full_turn_ops"),
            ("full_turns=2", "full_turns=1", "SUMMARY full_turns"),
            ("paused_turns=3", "paused_turns=-1", "SUMMARY paused_turns"),
            ("full_turn_ops=17900", "full_turn_ops=-1", "SUMMARY full_turn_ops"),
            ("map_mode=line", "map_mode=band", "COST band_ops"),
            ("band_cells=-1", "band_cells=2", "COST band_cells"),
            ("band_ops=-1", "band_ops=2", "COST band_ops"),
        ]
        for old, new, message in bad_cases:
            with self.subTest(old=old, new=new):
                modified = [line.replace(old, new, 1) for line in carto2b_game()]
                result = parse_game("carto2_seed42_r0.log", modified)
                self.assertFalse(result["log_complete"])
                self.assertIn(message, " ".join(result["errors"]))

    def test_carto2b_expiry_not_confused_with_search_ready_in_1974(self):
        logs = [
            log("CARTO2_START", when="1970-1-1", seed=100, mapx=1024, mapy=1024),
            log("CARTO2_PAIR", when="1970-1-1", id=0,
                key="freight:0:100:200", src=100, dst=200, dist=240),
            log("CARTO2_COST", when="1970-1-2", id=0,
                key="freight:0:100:200", map_mode="line",
                line_ops=50, band_ops=-1, line_ticks=0, band_ticks=-1,
                line_cells=10, band_cells=-1),
            log("CARTO2_SEARCH", when="1970-3-1", id=0,
                key="freight:0:100:200", mode="free", phase="end",
                outcome="OK", ready=1, iters=20, ops=1000, ticks=0, path_dist=260),
            log("CARTO2_SEARCH", when="1970-3-2", id=0,
                key="freight:0:100:200", mode="guided", phase="end",
                outcome="OK", ready=1, iters=18, ops=900, ticks=0, path_dist=258),
            log("CARTO2_SUMMARY", when="1974-11-30", phase="done",
                pairs=1, mapped=1, completed=1, ready=0, year=1974),
        ]
        record = parse_game("carto2_seed42_r0.log", logs)
        self.assertTrue(record["log_complete"], record["errors"])
        self.assertEqual(record["rows"][0]["free"]["ready_at_search"], 1)
        self.assertIsNone(record["rows"][0]["free"]["ready1974"])
        self.assertIsNone(record["ready_at_end_snapshot"])
        self.assertFalse(record["readiness"]["snapshot_on_end_date"])
        self.assertEqual(record["search_partial"]["ready_at_search"], 2)
        self.assertEqual(analyze_sources([("carto2_seed42_r0.log", logs)])
                         ["policies"]["carto2"]["astar_ok_pairs"]["count"], 1)

    def test_carto2b_turn_logs_sampled_but_summary_authoritative(self):
        """Runtime omits CARTO2_TURN when fewer than 2500 ops remain."""
        samples = [line for line in carto2b_game() if
                   "CARTO2_TURN phase=full ops=8800" not in line]
        record = parse_game("reference_seed42_r0.log", samples)
        self.assertTrue(record["log_complete"], record["errors"])
        self.assertEqual(record["v309_turns"]["observed_full_turns"], 1)
        self.assertEqual(record["v309_turns"]["observed_full_turn_ops"]["sum"], 9100)
        self.assertEqual(record["v309_turns"]["reported_full_turns"], 2)
        self.assertEqual(record["v309_turns"]["reported_full_turn_ops"], 17900)
        self.assertEqual(record["v309_turns"]["unlogged_full_turns"], 1)
        self.assertEqual(record["v309_turns"]["unlogged_full_turn_ops"], 8800)
        report = analyze_sources([("reference_seed42_r0.log", samples)])
        result, manifest = harness()
        result["seeds"] = manifest["configuration"]["seeds"] = [42]
        result["games"] = result["games"][:1]
        manifest["games"] = manifest["games"][:1]
        validate_campaign(report, result, manifest)
        self.assertTrue(report["policies"]["reference"]["complete"])

    def test_carto2b_complete_gate_requires_evidence_and_both_searches(self):
        log_rows = carto2b_game()
        report = analyze_sources([("reference_seed42_r0.log", log_rows)])
        self.assertTrue(report["policies"]["reference"]["log_complete"])
        self.assertFalse(report["policies"]["reference"]["complete"])
        result, manifest = harness()
        result["seeds"] = manifest["configuration"]["seeds"] = [42]
        result["games"] = result["games"][:1]
        manifest["games"] = manifest["games"][:1]
        validate_campaign(report, result, manifest)
        self.assertTrue(report["policies"]["reference"]["complete"])
        missing = [row for row in log_rows
                   if "CARTO2_SEARCH id=1" not in row or "mode=guided" not in row]
        failed = analyze_sources([("reference_seed42_r0.log", missing)])
        validate_campaign(failed, result, manifest)
        self.assertFalse(failed["policies"]["reference"]["complete"])
        self.assertTrue(failed["policies"]["reference"]["campaign_verified"])

    def test_provenance_horizon_and_source_sha(self):
        report = analyze_sources(sources())
        validate_campaign(report, *harness())
        self.assertTrue(report["policies"]["reference"]["complete"])
        self.assertTrue(report["policies"]["reference"]["campaign_verified"])
        self.assertEqual(report["provenance"]["expected_last_year"], 1974)
        self.assertEqual(report["provenance"]["git_sha"], "fixture-sha")
        self.assertEqual(report["provenance"]["source_bundle_sha256"], "fixture-bundle")

    def test_actual_start_reservoir_seed_and_manifest_source_provenance(self):
        """START emits RLW sample seed; bundle SHA + Git SHA live in manifest."""
        actual = game()
        actual[0] = log("CARTO2_START", when="1970-1-20", version=1,
                        mapx=1024, mapy=1024, start_year=1970,
                        years=5, seed=1791467322, bit="24_25_26")
        actual.insert(1, log("CARTO2_SUMMARY", when="1970-1-20",
                             phase="progress", pairs=0, mapped=0,
                             completed=0, ready=0, map_ops=0,
                             search_ops=0, year=1970))
        report = analyze_sources([("reference_seed42_r0.log", actual)])
        policy = report["policies"]["reference"]
        self.assertTrue(policy["log_complete"], policy["errors"])
        self.assertEqual(policy["games"][0]["reservoir_seed"], 1791467322)
        result, manifest = harness()
        result["seeds"] = [42]
        result["games"] = result["games"][:1]
        manifest["configuration"]["seeds"] = [42]
        manifest["games"] = manifest["games"][:1]
        validate_campaign(report, result, manifest)
        self.assertTrue(policy["complete"], policy["campaign_errors"])
        self.assertEqual(policy["games"][0]["summary"]["phase"], "done")

    def test_runtime_cancel_nullable_distance_and_year_of_readiness(self):
        original = game()
        changed = [line.replace("outcome=DEAD", "outcome=CANCEL", 1)
                   .replace("path_dist=-1", "path_dist=NA", 1)
                   for line in original]
        changed = [line.replace("path_dist=242", "path_dist=-1", 1)
                   for line in changed]
        record = parse_game("reference_seed42_r0.log", changed)
        self.assertTrue(record["log_complete"], record["errors"])
        self.assertIsNone(record["rows"][0]["quality"])
        self.assertIsNone(record["rows"][0]["guided"]["path_dist"])
        self.assertEqual(record["rows"][2]["guided"]["outcome"], "CANCEL")
        self.assertIsNone(record["rows"][2]["guided"]["path_dist"])
        self.assertEqual(record["rows"][0]["free"]["ready1974"], 1)
        early = [line.replace("1974-12-31", "1972-6-30") for line in changed]
        early = [line.replace("year=1974", "year=1972") for line in early]
        early_rec = parse_game("reference_seed42_r0.log", early)
        self.assertTrue(early_rec["log_complete"], early_rec["errors"])
        self.assertIsNone(early_rec["rows"][0]["free"]["ready1974"])
        self.assertEqual(early_rec["rows"][0]["free"]["ready_at_search"], 1)
        self.assertIsNone(early_rec["ready_at_end_snapshot"])

    def test_real_256_progress_fixture_mapped_partial_and_reference_excluded(self):
        partial = [
            log("CARTO2_START", when="1970-1-20", version=1,
                mapx=256, mapy=256, start_year=1970,
                years=5, seed=1791467322, bit="24_25_26"),
            log("CARTO2_SUMMARY", when="1970-1-20", phase="progress",
                pairs=0, mapped=0, completed=0, ready=0, year=1970),
            log("CARTO2_PAIR", when="1970-2-22", id=0,
                key="freight:1:9815:43468", src=9815, dst=43468,
                dist=248, score=28539, source="long"),
            log("CARTO2_PAIR", when="1970-2-22", id=1,
                key="freight:8:57983:28395", src=57983, dst=28395,
                dist=224, score=13664, source="live"),
            log("CARTO2_COST", when="1970-5-16", id=0,
                key="freight:1:9815:43468", source="long", score=28539,
                line_ops=22683, band_ops=113533, line_ticks=0,
                band_ticks=0, line_cells=18, band_cells=90, valid=1),
            log("CARTO2_SUMMARY", when="1970-7-19", phase="progress",
                pairs=2, mapped=1, completed=0, ready=0,
                map_ops=314870, search_ops=0, year=1970),
        ]
        report = analyze_sources([("carto2_seed42_r0.log", partial),
                                  ("reference_seed42_r0.log", ["plain engine log"])])
        self.assertEqual(len(report["policies"]), 1)
        self.assertEqual(len(report["ignored_no_carto2_logs"]), 1)
        policy = report["policies"]["carto2"]
        self.assertFalse(policy["log_complete"])
        self.assertEqual(policy["aggregate"]["pairs"], 0)
        self.assertEqual(policy["mapped_partial"]["mapped"], 1)
        self.assertEqual(policy["mapped_partial"]["band_ops"]["sum"], 113533)
        self.assertEqual(policy["mapped_partial"]["line_ops"]["sum"], 22683)
        self.assertEqual(policy["games"][0]["pair_sources"], {"long": 1, "live": 1})
        self.assertEqual(policy["games"][0]["summary"]["phase"], "progress")
        result, manifest = harness()
        result["campaign_id"] = manifest["campaign_id"] = "smoke"
        result["years"] = manifest["configuration"]["years"] = 1
        result["expected_last_year"] = 1970
        result["map_size"] = manifest["configuration"]["map_size"] = 8
        result["seeds"] = manifest["configuration"]["seeds"] = [42]
        result["games"] = [{"policy_id": "carto2", "seed": 42, "repeat": 0,
                            "game_status": "complete", "game_ok": True,
                            "unattributed_errors": [],
                            "engine_log_path": "carto2_seed42_r0.log",
                            "companies": {"OpexAI": {"horizon_complete": True}}}]
        manifest["games"] = [{"policy_id": "carto2", "seed": 42, "repeat": 0}]
        validate_campaign(report, result, manifest)
        self.assertFalse(policy["complete"])
        self.assertIn("horizon attendu fin 1974", " ".join(policy["campaign_errors"]))

    def test_missing_search_does_not_fabricate_a_pair(self):
        original = game()
        broken = [line for line in original
                  if not ("CARTO2_SEARCH id=0" in line and "mode=guided" in line)]
        record = parse_game("reference_seed42_r0.log", broken)
        self.assertEqual((record["pairs_seen"], record["pairs_valid"]), (4, 3))
        self.assertFalse(record["log_complete"])
        self.assertIn("free/guided absent", " ".join(record["errors"]))

    def test_partial_search_by_seed_mode_aggregate_and_no_double_count(self):
        sources = [(f"carto2_seed{seed}_r0.log", partial_search_game(seed))
                   for seed in (42, 100, 999)]
        report = analyze_sources(sources)
        policy = report["policies"]["carto2"]
        samples = {g["seed"]: g for g in policy["games"]}
        self.assertEqual([g["pairs_valid"] for g in policy["games"]], [1, 0, 0])
        self.assertFalse(policy["complete"])
        self.assertFalse(policy["log_complete"])
        self.assertEqual(samples[42]["search_partial"]["count"], 2)
        self.assertEqual(samples[42]["search_partial"]["iters"]["sum"], 6)
        self.assertEqual(samples[42]["search_partial"]["ops"]["sum"], 12136)
        self.assertEqual(samples[42]["search_partial"]["outcomes"], {"CANCEL": 2})
        self.assertEqual(samples[100]["search_partial"]["count"], 0)
        self.assertEqual(samples[100]["search_partial"]["ops"]["sum"], 0)
        self.assertEqual(samples[999]["search_partial"]["count"], 1)
        self.assertEqual(samples[999]["search_partial"]["modes"]["free"]["iters"]["sum"], 442)
        self.assertEqual(samples[999]["search_partial"]["modes"]["free"]["ops"]["sum"], 862164)
        self.assertEqual(samples[999]["search_partial"]["modes"]["guided"]["count"], 0)
        self.assertEqual(samples[999]["search_partial_records"][0]["path_dist"], None)
        total = policy["search_partial"]
        self.assertEqual(total["count"], 3)
        self.assertEqual(total["distinct_pair_ids"], 2)
        self.assertEqual(total["iters"]["sum"], 448)
        self.assertEqual(total["ops"]["sum"], 874300)
        self.assertEqual(total["ticks"]["sum"], 0)
        self.assertEqual(total["outcomes"], {"CANCEL": 3})
        self.assertEqual(total["modes"]["free"]["count"], 2)
        self.assertEqual(total["modes"]["free"]["iters"]["sum"], 444)
        self.assertEqual(total["modes"]["free"]["ops"]["sum"], 867361)
        self.assertEqual(total["modes"]["guided"]["count"], 1)
        self.assertEqual(total["modes"]["guided"]["iters"]["sum"], 4)
        self.assertEqual(total["modes"]["guided"]["ops"]["sum"], 6939)
        self.assertEqual(total["ready_at_search"], 0)
        self.assertEqual(policy["aggregate"]["pairs"], 1)  # paired stats unchanged
        rendered = render_markdown(report)
        for fragment in ("SEARCH observés", "seed42/r0", "seed100/r0",
                         "seed999/r0", "862164", "874300", "CANCEL",
                         "Toutes graines"):
            self.assertIn(fragment, rendered)
        self.assertEqual(
            json.loads(json.dumps(report))["policies"]["carto2"]
            ["search_partial"]["ops"]["sum"], 874300)

    def test_malformed_partial_search_is_not_aggregated(self):
        broken = [line.replace("ops=862164", "ops=nan")
                  for line in partial_search_game(999)]
        record = parse_game("carto2_seed999_r0.log", broken)
        self.assertEqual(record["search_partial"]["count"], 0)
        self.assertEqual(record["search_partial"]["ops"]["sum"], 0)
        self.assertFalse(record["log_complete"])
        self.assertIn("free SEARCH ops absent", " ".join(record["errors"]))

    def test_partial_campaign_strict_gate_even_with_valid_harness(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            for seed in (42, 100, 999):
                (root / f"carto2_seed{seed}_r0.log").write_text(
                    "".join(partial_search_game(seed)), encoding="utf-8")
            result, manifest = harness()
            result["seeds"] = manifest["configuration"]["seeds"] = [42, 100, 999]
            result["games"] = []
            manifest["games"] = []
            for seed in (42, 100, 999):
                entry = {"policy_id": "carto2", "seed": seed, "repeat": 0}
                manifest["games"].append(entry)
                result["games"].append({
                    **entry, "game_status": "complete", "game_ok": True,
                    "engine_log_path": f"/work/results/carto2_seed{seed}_r0.log",
                    "unattributed_errors": [],
                    "companies": {"OpexAI": {"horizon_complete": True}},
                })
            result_path, manifest_path = root / "result.json", root / "manifest.json"
            result_path.write_text(json.dumps(result), encoding="utf-8")
            manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
            with contextlib.redirect_stdout(io.StringIO()) as stdout:
                status = main([str(root), "--result-json", str(result_path),
                               "--manifest", str(manifest_path),
                               "--format", "markdown", "--require-complete"])
            self.assertEqual(status, 1)
            self.assertIn("862164", stdout.getvalue())
            report = analyze_paths([root], result_json=result_path,
                                   manifest=manifest_path)
            self.assertFalse(report["policies"]["carto2"]["complete"])
            self.assertTrue(report["policies"]["carto2"]["campaign_verified"])
            self.assertEqual(report["policies"]["carto2"]["search_partial"]
                             ["outcomes"], {"CANCEL": 3})

    def test_duplicate_and_conflicting_pair_provenance_are_invalid(self):
        original = game()
        first_search = next(line for line in original if "CARTO2_SEARCH id=0" in line)
        dup = parse_game("reference_seed42_r0.log", original + [first_search])
        self.assertFalse(dup["log_complete"])
        self.assertIn("dupliqué", " ".join(dup["errors"]))
        conflict = [line.replace("key=freight:0:100:200", "key=alien", 1)
                    if "CARTO2_SEARCH id=0 " in line and " mode=free " in line else line
                    for line in original]
        wrong = parse_game("reference_seed42_r0.log", conflict)
        self.assertEqual(wrong["pairs_valid"], 3)
        self.assertIn("clé discordante", " ".join(wrong["errors"]))

    def test_bad_metric_and_contradictory_readiness_fail_closed(self):
        original = game()
        replacements = [
            ("band_ops=120", "band_ops=-1", "band_ops"),
            ("band_cells=30", "band_cells=1", "band_cells"),
            ("mode=guided phase=end outcome=OK iters=80",
             "mode=guided phase=end outcome=ABND iters=80", "ready=1"),
            ("ticks=0 ready=1", "ticks=-2 ready=1", "ticks"),
        ]
        for before, after, fragment in replacements:
            with self.subTest(fragment=fragment):
                changed = [line.replace(before, after, 1) for line in original]
                record = parse_game("reference_seed42_r0.log", changed)
                self.assertFalse(record["log_complete"])
                self.assertIn(fragment, " ".join(record["errors"]))

    def test_safety_and_bad_summary_fail_closed(self):
        for changes in (
                [log("CARTO2_SAFETY", phase="abort", reason="budget_exceeded")],
                [log("CARTO2_SUMMARY", phase="unsafe", pairs=4, year=1974)],
                [log("CARTO2_SUMMARY", phase="done", pairs=4, year=1973)],
        ):
            record = parse_game("reference_seed42_r0.log", game() + changes)
            self.assertFalse(record["log_complete"])
        explicit_seed = [line.replace("seed=42", "seed=1791467322 game_seed=42")
                         for line in game()]
        wrong_seed = parse_game("reference_seed7_r0.log", explicit_seed)
        self.assertIn("game_seed START différent", " ".join(wrong_seed["errors"]))

    def test_unhealthy_or_wrong_provenance_fail_closed(self):
        for failure in ("source", "years", "unhealthy", "games", "image", "debug"):
            with self.subTest(failure=failure):
                report = analyze_sources(sources())
                result, manifest = harness()
                if failure == "source":
                    manifest["git"]["sha"] = "wrong-sha"
                elif failure == "years":
                    manifest["configuration"]["years"] = 3
                elif failure == "unhealthy":
                    result["games"][0]["companies"]["OpexAI"]["horizon_complete"] = False
                elif failure == "games":
                    manifest["games"].pop()
                elif failure == "image":
                    del manifest["execution"]["options"]["docker_image_id"]
                else:
                    manifest["execution"]["options"]["script_debug"] = False
                validate_campaign(report, result, manifest)
                policy = report["policies"]["reference"]
                self.assertFalse(policy["complete"])
                self.assertFalse(policy["campaign_verified"])

    def test_cli_gzip_and_require_complete(self):
        with tempfile.TemporaryDirectory() as name:
            root = Path(name)
            with gzip.open(root / "reference_seed42_r0.log.gz", "wt", encoding="utf-8") as f:
                f.writelines(game())
            result, manifest = harness()
            result["seeds"] = [42]
            result["games"] = result["games"][:1]
            manifest["configuration"]["seeds"] = [42]
            manifest["games"] = manifest["games"][:1]
            result_path, manifest_path = root / "results.json", root / "manifest.json"
            result_path.write_text(json.dumps(result), encoding="utf-8")
            manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
            with contextlib.redirect_stdout(io.StringIO()):
                self.assertEqual(main([str(root), "--format", "json",
                                       "--require-complete"]), 1)
                self.assertEqual(main([str(root), "--format", "json",
                                       "--require-complete",
                                       "--result-json", str(result_path),
                                       "--manifest", str(manifest_path)]), 0)
            report = analyze_paths([root], result_json=result_path,
                                   manifest=manifest_path)
            self.assertTrue(report["policies"]["reference"]["complete"])
            self.assertEqual(report["policies"]["reference"]["aggregate"]["pairs"], 4)


if __name__ == "__main__":
    unittest.main()
