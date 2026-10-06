from pathlib import Path
import json
import tempfile
import unittest

from analyse_c121_kdec_cold_shadow import analyse_campaign, counts, decode_log, distribution, group_report, parse_event, resolve_log

PREFIX = "[2026-10-02 14:00:00] dbg: [script:4] [0] [I] C121_KDEC_COLD_"
CANDIDATE = ("SHADOW state=cold line=7 samples=0 finance=100 k_dec=500 denom=500 "
             "cold_denom=100 score=2 cold_score=10 rank=-1 cold_rank=0 affected=1 "
             "head_flip=1 year=1971 month=2 day=3")
SUMMARY = ("SUMMARY cold=1 warm=0 affected=1 rank_up=1 entered=1 head_flip=1 "
           "head_mode=air k_dec=500 year=1971 month=2 day=3")


class DecoderTests(unittest.TestCase):
    def log(self, lines):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "engine.log"
            path.write_text("\n".join(PREFIX + row for row in lines), encoding="utf-8")
            return decode_log(path)

    def test_game_date_not_wall_time(self):
        event = parse_event(PREFIX + CANDIDATE)
        self.assertEqual(event["date"], "1971-02-03")
        self.assertEqual(event["score"], 2)

    def test_ignore_other_company(self):
        self.assertIsNone(parse_event((PREFIX + CANDIDATE).replace("[0]", "[1]")))

    def test_no_date_is_invalid(self):
        with self.assertRaises(KeyError):
            parse_event(PREFIX + CANDIDATE.split(" year=")[0])

    def test_repeated_selections_are_not_deduplicated(self):
        passes, candidates, _ = self.log([CANDIDATE, SUMMARY] * 2)
        self.assertEqual(len(passes), 2)
        self.assertEqual([row["selection"] for row in candidates], [0, 1])

    def test_flags_recomputed(self):
        self.assertEqual(counts([parse_event(PREFIX + CANDIDATE)])["entered"], 1)
        with self.assertRaisesRegex(ValueError, "flag"):
            self.log([CANDIDATE.replace("affected=1", "affected=0"), SUMMARY])

    def test_summary_mismatch_rejected(self):
        with self.assertRaisesRegex(ValueError, "summary"):
            self.log([CANDIDATE, SUMMARY.replace("cold=1", "cold=2")])

    def test_truncated_selection_rejected(self):
        with self.assertRaisesRegex(ValueError, "unfinished"):
            self.log([CANDIDATE])

    def test_date_rollover(self):
        passes, _, _ = self.log([CANDIDATE.replace("year=1971", "year=1972"), SUMMARY.replace("year=1971", "year=1972")])
        self.assertEqual(passes[0]["date"], "1972-02-03")

    def test_warm_is_not_affected(self):
        row = parse_event(PREFIX + CANDIDATE)
        row.update(state="warm", samples=1, cold_denom=500, cold_score=2, cold_rank=-1, affected=0, head_flip=0)
        self.assertEqual(counts([row]), dict(cold=0, warm=1, affected=0, rank_up=0, entered=0, head_flip=0))

    def test_actual_funded_only(self):
        _, _, funded = self.log([CANDIDATE, SUMMARY, "FUNDED line=7 added=1 samples=0 year=1971 month=2 day=5"])
        self.assertEqual(funded[0]["date"], "1971-02-05")

    def test_empty_ratio_is_unknown(self):
        self.assertIsNone(distribution([])["mean"])
        self.assertEqual(distribution([5])["median"], 5)

    def test_zero_score_ratio_is_unknown(self):
        row = parse_event(PREFIX + CANDIDATE)
        row["score"] = 0
        result = group_report([parse_event(PREFIX + SUMMARY)], [row])
        self.assertEqual(result["affected_zero_score"], 1)
        self.assertEqual(result["score_ratio"]["n"], 0)

    def test_work_path_mapping(self):
        self.assertEqual(resolve_log("/work/results/a.log", Path("root")), Path("root/results/a.log"))

    def test_real_smoke_fixture(self):
        path = Path(__file__).parent / "fixtures" / "c121_kdec_cold_smoke_20261002.log"
        if not path.exists():
            self.skipTest("real smoke fixture pending")
        passes, rows, funded = decode_log(path)
        self.assertEqual(len(passes), 87)
        self.assertEqual(rows, [])
        self.assertEqual(funded, [])

    def test_real_diagnostic_cold_warm_and_funding_fixture(self):
        path = Path(__file__).parent / "fixtures" / "c121_kdec_cold_warm_20261002.log"
        passes, rows, funded = decode_log(path)
        self.assertEqual(len(passes), 2)
        self.assertEqual(len(rows), 7)
        self.assertEqual(sum(row["samples"] > 0 for row in rows), 1)
        self.assertEqual(len(funded), 2)


class CampaignTests(unittest.TestCase):
    def campaign(self, exposed=0, empty=False, unhealthy=False, years=6):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            games = []
            for seed in range(5):
                lines = [CANDIDATE, SUMMARY] if seed < exposed else [SUMMARY.replace(
                    "cold=1 warm=0 affected=1 rank_up=1 entered=1 head_flip=1",
                    "cold=0 warm=0 affected=0 rank_up=0 entered=0 head_flip=0")]
                name = f"seed{seed}.log"
                (root / name).write_text("\n".join(PREFIX + row for row in lines), encoding="utf-8")
                games.append(dict(seed=seed, repeat=0, policy_id="variant", engine_log_path=name,
                                  game_ok=not (unhealthy and seed == 0)))
            payload = dict(campaign_id="test", policy_id="reference", seeds=list(range(5)),
                           repeats=1, years=years, expected_last_year=1975,
                           source_bundle_sha256="test-bundle", games=games,
                           policy_comparison=dict(variant_policy_id="variant"))
            if empty:
                payload["games"].pop()
            path = root / "campaign.json"
            path.write_text(json.dumps(payload), encoding="utf-8")
            return analyse_campaign(path, root=root)

    def test_zero_exposure_negligible(self):
        report = self.campaign()
        self.assertEqual(report["exposure_gate"], "negligible")
        self.assertEqual(len(report["by_seed_year"]), 30)

    def test_three_seeds_material(self):
        report = self.campaign(exposed=3)
        self.assertEqual(report["exposure_gate"], "material")
        self.assertEqual(report["head_flip_seeds"], [0, 1, 2])
        self.assertEqual(report["summary"]["cold_lines"], 3)
        self.assertEqual(report["summary"]["score_ratio"]["mean"], 5)
        self.assertIsNone(report["by_line"][0]["first_funded_date"])

    def test_two_seeds_intermediate(self):
        self.assertEqual(self.campaign(exposed=2)["exposure_gate"], "intermediate")

    def test_incomplete_not_inert(self):
        self.assertEqual(self.campaign(empty=True)["exposure_gate"], "non_validated")

    def test_unhealthy_not_inert(self):
        self.assertEqual(self.campaign(unhealthy=True)["exposure_gate"], "non_validated")

    def test_smoke_cannot_close_hypothesis(self):
        self.assertEqual(self.campaign(years=2)["exposure_gate"], "short_sample")


class ProbeContracts(unittest.TestCase):
    def test_both_captures_follow_current_score(self):
        root = Path(__file__).resolve().parents[1]
        text = (root / "ai/OpexAI/projects_selection.nut").read_text(encoding="utf-8")
        selection = text[text.index("function OpexProjectSelectAffordable"):text.index("function OpexProjectSelectionScore")]
        captures = selection.split("OpexC121KDecColdShadowCandidate")
        self.assertEqual(len(captures), 3)
        for prior in captures[:2]:
            self.assertIn("project.fundScore <- OpexProjectScore", prior)
            between = prior[prior.rindex("project.fundScore <- OpexProjectScore"):]
            self.assertNotIn("foreach", between)

    def test_date_and_funding_do_not_use_task_state(self):
        root = Path(__file__).resolve().parents[1]
        text = (root / "ai/OpexAI/projects_selection.nut").read_text(encoding="utf-8")
        probe = text[text.index("function OpexC121KDecColdShadowCandidate"):text.index("function OpexProjectSelectAffordable")]
        self.assertNotIn("OpexDecide(", probe)
        self.assertIn('line.mode != "air"', probe)
        self.assertIn('" day=" + AIDate.GetDayOfMonth(date)', probe)


if __name__ == "__main__":
    unittest.main()
