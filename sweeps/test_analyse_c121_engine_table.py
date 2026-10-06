"""Contrats de la sonde passive C121_ENGTAB et de l'analyseur hors ligne."""
from pathlib import Path
import contextlib
import io
import json
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "sweeps"))

from analyse_c121_engine_table import (  # noqa: E402
    analyse_paths,
    analyse_texts,
    asymmetry_class,
    bin_index,
    log_edges,
    main,
    parse_line,
    parse_log_text,
    portfolio_parts,
    quantile_edges,
    reconstruct,
)
from campaign_freeze import parse_ai_settings  # noqa: E402

AI = ROOT / "ai" / "OpexAI"
PREFIX = "[2026-10-02 14:00:00] dbg: [script:4] [2] [I] "


def plan_line(pass_id, key, dist, score, eng, arm="newpair", ap=3, pax=50,
              date="1970-06-01", pax_b=None):
    other = pax if pax_b is None else pax_b
    return (
        "C121_ENGTAB_PLAN pass=%s date=%s key=%s arm=%s ap=%s dist=%s "
        "paxRawA=%s paxRawB=%s paxA=%s paxB=%s mailRawA=0 mailRawB=0 eng=%s "
        "score=%s P=%s C=1000 dScore=%s dP=%s dC=1000 pfScore=-1 pfP=-1 pfC=-1 "
        "n=1 P_n1=-1 C_n1=-1 P_n2=-1 C_n2=-1 imm=0 kdec=-1 init=0 split=0"
        % (pass_id, date, key, arm, ap, dist, pax, other, pax, other, eng,
           score, score, score, score)
    )


def eng_line(pass_id, key, eng, score, evaluated=1, upper=None):
    if upper is None:
        upper = score if score != -1 else 0
    profit = score
    capital = 1000 if score != -1 else -1
    return (
        "C121_ENGTAB_ENG pass=%s key=%s eng=%s upper=%s eval=%s score=%s P=%s C=%s"
        % (pass_id, key, eng, upper, evaluated, score, profit, capital)
    )


def positive_log(arm="newpair"):
    lines = ["C121_ENGTAB_PASS pass=1 date=1970-06-01 engines=3:7,8"]
    for dist, score in zip((10, 20, 30, 40, 50, 60), (600, 500, 400, 300, 200, 100)):
        key = "1-%s-3-%s" % (dist, arm)
        lines.append(eng_line(1, key, 8, score - 50))
        lines.append(eng_line(1, key, 7, score))
        lines.append(plan_line(1, key, dist, score, 7, arm=arm))
    return "\n".join(lines) + "\n"


def winner_log(winner, other, winner_score, other_score):
    lines = ["C121_ENGTAB_PASS pass=1 date=1970-06-01 engines=3:7,8,9"]
    for dist in (10, 20, 30, 40, 50, 60):
        key = "4-%s-3-newpair" % dist
        lines.append(eng_line(1, key, other, other_score))
        lines.append(eng_line(1, key, winner, winner_score))
        lines.append(plan_line(1, key, dist, winner_score, winner))
    return "\n".join(lines) + "\n"


class ParseTests(unittest.TestCase):
    def test_openttd_prefix_and_raw_line(self):
        raw = PREFIX + plan_line(3, "1-2-3-newpair", 10, 6.5, 7)
        event = parse_line(raw)
        self.assertEqual(event["kind"], "PLAN")
        self.assertEqual(event["pass"], 3)
        self.assertEqual(event["date"], "1970-06-01")
        self.assertEqual(event["key"], "1-2-3-newpair")
        self.assertEqual(event["arm"], "newpair")
        self.assertEqual(event["dScore"], 6.5)
        self.assertEqual(event["pfP"], -1)
        bare = parse_line("C121_ENGTAB_ENG pass=3 key=1-2-3-newpair eng=8 upper=12.5 eval=0 score=-1 P=-1 C=-1")
        self.assertEqual(bare["kind"], "ENG")
        self.assertEqual(bare["upper"], 12.5)
        self.assertEqual(bare["eval"], 0)
        self.assertIsNone(parse_line("C78_AIRPAIR arm=newpair"))
        with_ge = parse_line(PREFIX + plan_line(3, "1-2-3-newpair", 10, 6.5, 7) + " ge=2 ge_est=223")
        self.assertEqual(with_ge["ge"], 2)
        self.assertEqual(with_ge["ge_est"], 223)
        self.assertNotIn("ge", event)

    def test_engines_signature_stays_text(self):
        event = parse_line("C121_ENGTAB_PASS pass=1 date=1970-01-02 engines=3:10,11;5:")
        self.assertEqual(event["engines"], "3:10,11;5:")
        self.assertEqual(event["date"], "1970-01-02")


class AttachmentTests(unittest.TestCase):
    def test_eng_binds_to_next_plan_and_hit_uses_last_plan(self):
        text = "\n".join([
            "C121_ENGTAB_PASS pass=1 date=1970-01-02 engines=3:7,8",
            eng_line(1, "1-2-3-newpair", 8, -1, evaluated=0, upper=1),
            eng_line(1, "1-2-3-newpair", 7, 6),
            plan_line(1, "1-2-3-newpair", 10, 6, 7),
            eng_line(1, "4-5-3-hubsite", 7, 2),
            plan_line(1, "4-5-3-hubsite", 20, 2, 7, arm="hubsite"),
            "C121_ENGTAB_PASS pass=2 date=1971-03-04 engines=3:7,9",
            "C121_ENGTAB_HIT pass=2 key=1-2-3-newpair",
            "C121_ENGTAB_HIT pass=2 key=9-9-3-newpair",
        ])
        rows, unresolved = reconstruct(parse_log_text(text), seed=42, game=0)
        plans = [row for row in rows if not row["hit"]]
        hits = [row for row in rows if row["hit"]]
        self.assertEqual(len(plans), 2)
        self.assertEqual(len(hits), 1)
        self.assertEqual(unresolved, 1)
        self.assertEqual([row["eng"] for row in plans[0]["engines_rows"]], [8, 7])
        self.assertEqual(plans[0]["engines_rows"][0]["eval"], 0)
        self.assertEqual(plans[0]["engines_rows"][0]["score"], -1)
        self.assertEqual(plans[0]["engine_set"], "3:7,8")
        self.assertEqual([row["eng"] for row in plans[1]["engines_rows"]], [7])
        self.assertEqual(hits[0]["eng"], 7)
        self.assertEqual(hits[0]["pass"], 2)
        self.assertEqual(hits[0]["year"], 1971)
        self.assertEqual(hits[0]["engine_set"], "3:7,9")
        self.assertEqual([row["eng"] for row in hits[0]["engines_rows"]], [8, 7])
        self.assertEqual(hits[0]["dScore"], 6)


class BinTests(unittest.TestCase):
    def test_quantile_bins_separate_six_distances(self):
        distances = [10, 20, 30, 40, 50, 60]
        edges = quantile_edges(distances, 6)
        indexes = [bin_index(value, edges, False) for value in distances]
        self.assertEqual(indexes, [0, 1, 2, 3, 4, 5])

    def test_log_edges_and_nonpositive_bin(self):
        edges = log_edges([1, 100], 2)
        self.assertAlmostEqual(edges[0], 1.0)
        self.assertAlmostEqual(edges[1], 10.0)
        self.assertAlmostEqual(edges[2], 100.0)
        self.assertEqual(bin_index(0, edges, True), 0)
        self.assertEqual(bin_index(1, edges, True), 0)
        self.assertEqual(bin_index(50, edges, True), 1)
        self.assertEqual(bin_index(100, edges, True), 1)

    def test_asymmetry_classes(self):
        self.assertEqual(asymmetry_class(100, 80), 0)
        self.assertEqual(asymmetry_class(50, 100), 1)
        self.assertEqual(asymmetry_class(10, 100), 2)
        self.assertEqual(asymmetry_class(0, 0), 0)
        self.assertEqual(asymmetry_class(-1, 40), 0)
        self.assertEqual(asymmetry_class(40, 100, high=0.5, low=0.2), 1)

    def test_duplicate_quantile_collapses(self):
        self.assertEqual(quantile_edges([5, 5, 5], 4), [5.0, 5.0])
        self.assertEqual(bin_index(5, [5.0, 5.0], False), 0)


class PortfolioTests(unittest.TestCase):
    def test_fund_score_proxy_uses_decision_fields_and_arm_margin(self):
        base = {
            "arm": "newpair", "init": 0, "split": 0,
            "P": 100, "C": 500, "dP": 600, "dC": 1000,
            "pfP": -1, "pfC": -1, "imm": 0, "kdec": -1,
        }
        profit, capital, proxy = portfolio_parts(base)
        self.assertEqual(profit, 600)
        self.assertEqual(capital, 1000)
        self.assertAlmostEqual(proxy, 1000 * 600 / 31000)
        cold = dict(base, kdec=50000, imm=10)
        self.assertAlmostEqual(portfolio_parts(cold)[2], 1000 * 600 / 50000)
        opened = dict(base, init=1)
        self.assertAlmostEqual(portfolio_parts(opened)[2], 1000 * 100 / (500 + 30000))
        split = dict(base, split=1, pfP=50, pfC=2000)
        self.assertAlmostEqual(portfolio_parts(split)[2], 1000 * 50 / (2000 + 30000))
        self.assertAlmostEqual(portfolio_parts(dict(base, arm="hubsite"))[2], 1000 * 600 / (1000 + 12000))
        self.assertAlmostEqual(portfolio_parts(dict(base, arm="hubhub"))[2], 1000 * 600 / (1000 + 2000))
        self.assertEqual(portfolio_parts(dict(base, dP=-1))[0], 100)
        self.assertIsNone(portfolio_parts(dict(base, dP=0, P=0))[2])


class CrossValidationTests(unittest.TestCase):
    def test_identical_seeds_keep_engine_and_order(self):
        report = analyse_texts([(42, positive_log()), (100, positive_log())])
        self.assertTrue(report["cv"]["available"])
        metrics = report["configs"]["dist-6"]["metrics"]
        self.assertEqual(metrics["agreement"], 1)
        self.assertEqual(metrics["regret"], 0)
        self.assertEqual(metrics["regret_unknown"], 0)
        self.assertEqual(metrics["top1"], 1)
        self.assertEqual(metrics["top5"], 1)
        self.assertEqual(metrics["spearman"], 1)
        self.assertEqual(metrics["pc_spearman"], 1)
        self.assertEqual(metrics["k95"], 1)
        self.assertEqual(metrics["top5_overlap"], 1)
        self.assertAlmostEqual(metrics["kept3"], 0.5)
        self.assertAlmostEqual(metrics["avoid3"], 0.5)
        self.assertAlmostEqual(metrics["kept5"], 5 / 6)
        self.assertEqual(metrics["error_median"], 0)
        self.assertEqual(metrics["error_p90"], 0)
        self.assertEqual(metrics["fallback_rate"], 0)
        self.assertEqual(report["configs"]["dxd-6"]["metrics"]["spearman"], 1)
        self.assertEqual(report["configs"]["dxd-6"]["metrics"]["agreement"], 1)
        self.assertEqual(report["configs"]["dist-6"]["mean_cells_with_n1"], 0)
        filled = analyse_texts([
            (42, positive_log().replace("P_n1=-1", "P_n1=400")),
            (100, positive_log().replace("P_n1=-1", "P_n1=400")),
        ])
        self.assertEqual(filled["configs"]["dist-6"]["mean_cells_with_n1"], 6)
        text = __import__("analyse_c121_engine_table").format_markdown(report)
        self.assertIn("dxd-8", text)
        self.assertIn("newpair", text)
        again = analyse_texts([(42, positive_log()), (100, positive_log())])
        self.assertEqual(
            again["configs"]["random"]["metrics"]["agreement"],
            report["configs"]["random"]["metrics"]["agreement"],
        )

    def test_held_out_engine_regret_and_context_fallback(self):
        report = analyse_texts([
            (42, winner_log(7, 8, 100, 10)),
            (100, winner_log(9, 7, 80, 40)),
        ])
        metrics = report["configs"]["dist-6"]["metrics"]
        self.assertEqual(metrics["agreement"], 0)
        self.assertAlmostEqual(metrics["regret"], 0.5)
        self.assertAlmostEqual(metrics["regret_unknown"], 0.5)
        self.assertEqual(metrics["fallback_rate"], 0)
        shifted = analyse_texts([
            (42, positive_log("newpair")),
            (100, positive_log("hubsite")),
        ])
        context = shifted["configs"]["dxd-6"]["metrics"]
        self.assertEqual(context["agreement"], 1)
        self.assertEqual(context["fallback_rate"], 1)
        self.assertEqual(shifted["configs"]["dist-6"]["metrics"]["fallback_rate"], 0)

    def test_one_seed_does_not_train_on_itself(self):
        report = analyse_texts([(42, positive_log())])
        self.assertFalse(report["cv"]["available"])
        self.assertIsNone(report["configs"]["dist-6"]["metrics"]["agreement"])
        self.assertIsNone(report["configs"]["random"]["metrics"]["top1"])

    def test_campaign_keeps_only_the_probe_arm(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            log = root / "probe_42.log"
            log.write_text(positive_log(), encoding="utf-8")
            other = root / "missing.log"
            campaign = {
                "arms": {
                    "light": "OpexAI[c121_air_economics=1]",
                    "probe": "OpexAI[c121_air_economics=1,probe_c121_engine_table=1]",
                },
                "games": [
                    {"arm": "light", "seed": 1, "log_path": str(other)},
                    {"arm": "probe", "seed": 42, "log_path": str(log)},
                    {"arm": "probe", "seed": 100, "health": {"engine_log_path": str(log)}},
                ],
            }
            path = root / "diag.json"
            path.write_text(json.dumps(campaign), encoding="utf-8")
            report = analyse_paths([path])
            self.assertEqual(report["counts"]["games"], 2)
            self.assertEqual(report["counts"]["seeds"], [42, 100])
            self.assertEqual(report["configs"]["dist-6"]["metrics"]["agreement"], 1)
            out = root / "out.json"
            stdout = io.StringIO()
            with contextlib.redirect_stdout(stdout):
                self.assertEqual(main([str(path), "--json-out", str(out), "--no-context"]), 0)
            self.assertIn("dist-6", stdout.getvalue())
            saved = json.loads(out.read_text(encoding="utf-8"))
            self.assertEqual(saved["schema"], "c121-engine-table-v1")
            self.assertNotIn("dxd-6", saved["configs"])
            self.assertIn("dxd-6-nocontext", saved["configs"])
            self.assertIn("dist-6", saved["configs"])
            self.assertIn("random", saved["configs"])


class ProbeContractTests(unittest.TestCase):
    def test_setting_global_and_guarded_lines(self):
        defaults = parse_ai_settings(AI / "info.nut")
        self.assertEqual(defaults["probe_c121_engine_table"], 0)
        info = (AI / "info.nut").read_text(encoding="utf-8")
        block = info.split('name = "probe_c121_engine_table"', 1)[1].split("AddSetting", 1)[0]
        for field in ("easy_value = 0", "medium_value = 0", "hard_value = 0", "custom_value = 0"):
            self.assertIn(field, block)
        self.assertIn("AICONFIG_BOOLEAN", block)
        self.assertIn("; 0 = off (default)", block)
        globals_pre = (AI / "globals_pre.nut").read_text(encoding="utf-8")
        self.assertIn("PROBE_C121_ENGINE_TABLE <- false;", globals_pre)
        self.assertIn("C121_ENGTAB_PASS <- 0;", globals_pre)
        self.assertIn("C121_ENGTAB_N1 <- null;", globals_pre)
        self.assertIn("C121_ENGTAB_N2 <- null;", globals_pre)
        settings = (AI / "settings.nut").read_text(encoding="utf-8")
        self.assertIn(
            'PROBE_C121_ENGINE_TABLE = AIController.GetSetting("probe_c121_engine_table") != 0;',
            settings)
        planning = (AI / "air_planning.nut").read_text(encoding="utf-8")
        econ = (AI / "air_economics_c121.nut").read_text(encoding="utf-8")
        catalog = (AI / "air_catalog_c121.nut").read_text(encoding="utf-8")
        joined = planning + econ + catalog
        for prefix in ("C121_ENGTAB_PASS", "C121_ENGTAB_ENG", "C121_ENGTAB_PLAN", "C121_ENGTAB_HIT"):
            self.assertIn(prefix, joined)
        logs = [
            line for line in planning.splitlines()
            if "AILog.Info" in line and "C121_ENGTAB_" in line
        ]
        self.assertEqual(len(logs), 4)
        for name in (
            "OpexC121EngTabEmitPass", "OpexC121EngTabEmitEng", "OpexC121EngTabEmitPruned",
            "OpexC121EngTabEmitPlan", "OpexC121EngTabEmitHit", "OpexC121EngTabBeginPass",
            "OpexC121EngTabAfterChoice",
        ):
            body = planning.split("function %s(" % name, 1)[1].split("\nfunction ", 1)[0]
            guard = body.index("if (!PROBE_C121_ENGINE_TABLE) return;")
            if "AILog.Info" in body:
                self.assertLess(guard, body.index("AILog.Info"))
        self.assertNotIn('AILog.Info("C121_ENGTAB_', econ)
        self.assertNotIn('AILog.Info("C121_ENGTAB_', catalog)
        self.assertEqual(planning.count("if (PROBE_C121_ENGINE_TABLE) OpexC121EngTabAfterChoice("), 3)
        self.assertEqual(planning.count("if (PROBE_C121_ENGINE_TABLE) OpexC121EngTabBeginPass("), 1)
        self.assertIn("if (PROBE_C121_ENGINE_TABLE) OpexC121EngTabEmitHit(plan);", catalog)
        needle = "if (best != null && candidate.upperScore < best.economics.decisionScore) break;"
        chooser = econ.split("function OpexC121ChooseRoutePlane(", 1)[1]
        self.assertIn(needle, chooser)
        self.assertTrue(chooser.split(needle, 1)[1].lstrip().startswith("if (PROBE_C121_ENGINE_TABLE)"))
        self.assertNotIn("C121_AIR_ONE_OR_TWO_PLANES", chooser)
        pair = econ.split("function OpexC121OneOrTwoWinner(", 1)[1].split(
            "function OpexC121WinnerEconomics(", 1)[0]
        self.assertIn("return { initial = chosen, full = chosen };", pair)
        self.assertLess(pair.index("if (PROBE_C121_ENGINE_TABLE)"),
                        pair.index("return { initial = chosen, full = chosen };"))
        self.assertNotIn("fixedPlanes = 0", pair)
        self.assertIn("OpexC121EngineEconomics(catalog, plan, plane, 1, false)", pair)
        self.assertIn("OpexC121EngineEconomics(catalog, plan, plane, 2, false)", pair)


if __name__ == "__main__":
    unittest.main()
