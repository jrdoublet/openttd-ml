"""V216 etape 1 : contrats statiques de la sonde passive des estimateurs.

docs/plan_v216_scores_avant_premier_rail_20261016.md section 3.5 : reglage declare a 0,
lu une seule fois, aucun appel hors `if (V216_PROBE`, et la sonde ne commande rien au jeu.
Ce n'est pas un test de VM NoAI ; le smoke 1x1 sur 3 ans complete ces contrats.
"""
from pathlib import Path
import re
import unittest
from po01c_generate import PAX_SOURCES, function


AI = Path(__file__).resolve().parents[1] / "ai" / "OpexAI"
PROBE = AI / "probe_v216.nut"


class TestV216Probe(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.info = (AI / "info.nut").read_text(encoding="utf-8")
        cls.settings = (AI / "settings.nut").read_text(encoding="utf-8")
        cls.probe = PROBE.read_text(encoding="utf-8")
        cls.sources = {p.name: p.read_text(encoding="utf-8")
                       for p in AI.glob("*.nut") if p.name != PROBE.name}

    def test_setting_retired_into_mask(self):
        self.assertNotIn('name = "v216_probe"', self.info)
        self.assertIn('max_value = 2147483647', self.info)

    def test_setting_read_once(self):
        self.assertEqual(self.settings.count('GetSetting("v216_probe")'), 0)
        self.assertEqual(sum(s.count('GetSetting("v216_probe")') for s in self.sources.values()), 0)
        self.assertIn('V216_PROBE = OpexProbeEnabled(536870912);', self.settings)
        self.assertIn("V216_PROBE <- false;", self.sources["globals_pre.nut"])

    def test_probe_is_required(self):
        self.assertIn('require("probe_v216.nut");', self.sources["main.nut"])

    def test_every_call_site_is_guarded(self):
        hooks = 0
        for name, text in self.sources.items():
            if name == "po01c_generators.nut":
                # PO01f copies the behavioral V216a coverage helpers, not probe
                # hooks. Their resumable call graph is checked in test_po01c.
                for _, helper in PAX_SOURCES:
                    if helper.startswith("OpexV216"):
                        text = text.replace(function(text, "OpexPO01C" + helper[4:]), "")
                publication = "  if (po01fContext.used) V216_COVER = po01fContext.cover;"
                self.assertEqual(text.count(publication), 1)
                text = text.replace(publication, "")
            for line in text.splitlines():
                if re.search(r"\bOpexV216(?!a)\w*\(|\bV216_(?!PROBE\b)\w+\s*=", line):
                    hooks += 1
                    self.assertRegex(line, r"if \(V216_PROBE\b", name + ": " + line.strip())
        # selection x3, K_dec, rejets x3, RAIL_BUILD, tick mensuel
        self.assertEqual(hooks, 11)  # +2 guarded rejection hooks in the PO01f copy

    def test_probe_never_commands_the_game(self):
        code = re.sub(r"/\*.*?\*/", "", self.probe, flags=re.S)
        calls = set(re.findall(r"\bAI\w+\.(\w+)\(", code))
        forbidden = [c for c in calls
                     if re.match(r"(Build|Remove|Demolish|Set|Sell|Clone|Start|Stop|Skip|Send|"
                                 r"Append|Insert|Delete|Change|Refit|Found|Fund|Buy|Pay)", c)]
        self.assertEqual(forbidden, [])
        # Ne reecrit aucun champ des projets ni des candidats.
        self.assertNotRegex(code, r"\b(project|p|c|candidate)\.\w+\s*(<-|=[^=])")

    def test_rail_build_hook_outside_decision_log(self):
        text = self.sources["task_rail.nut"]
        hook = text.index("if (V216_PROBE && result.ok) OpexV216OnRailBuild(candidate);")
        self.assertLess(hook, text.index('OpexDecide("RAIL_BUILD"'))
        self.assertEqual(text[hook:].split("\n")[1].strip(), "if (DECISION_LOG) {")


class TestV216aGhostDemand(unittest.TestCase):
    """V216a : correction de la demande rail pax, inerte a 0, un seul point d'insertion."""

    @classmethod
    def setUpClass(cls):
        cls.info = (AI / "info.nut").read_text(encoding="utf-8")
        cls.sources = {p.name: p.read_text(encoding="utf-8") for p in AI.glob("*.nut")}

    def test_setting_default_qualified(self):
        block = re.search(r'name = "v216a_ghost_demand",(.*?)\}\);', self.info, re.S)
        self.assertIsNotNone(block)
        for level in ("easy_value", "medium_value", "hard_value", "custom_value"):
            self.assertRegex(block.group(1), level + r" = 1\b")
        self.assertIn("V216A_GHOST_DEMAND <- 0;", self.sources["globals_pre.nut"])
        self.assertEqual(sum(s.count('GetSetting("v216a_ghost_demand")') for s in self.sources.values()), 1)

    def test_single_guarded_insertion(self):
        calls = [(n, i) for n, t in self.sources.items() if n != "probe_v216.nut"
                 for i, l in enumerate(t.splitlines()) if "OpexV216aScaleDemand(" in l]
        self.assertEqual({n for n, _ in calls}, {"candidates.nut"})
        lines = self.sources["candidates.nut"].splitlines()
        guard = min(i for _, i in calls) - 1
        self.assertEqual(lines[guard].strip(), 'if (V216A_GHOST_DEMAND > 0 && kind == "pax") {')
        self.assertLess(self.sources["candidates.nut"].index("OpexV216aScaleDemand("),
                        self.sources["candidates.nut"].index("local economics = OpexLineEconomics(catalog, cargo, distance, monthly"))


class TestAnalyzeV216(unittest.TestCase):
    def test_parser_and_first_rail_pax(self):
        import sys, tempfile
        sys.path.insert(0, str(Path(__file__).resolve().parent))
        import analyze_v216 as a
        pre = "[t] dbg: [script:4] [0] [I] OPEX 1971-3-2 "
        lines = [
            pre + "V216_DECOMP seq=1 role=ranked rank=0 key=air|1 finance=10 affordable=1 tier=0 select_score=50 fund_profit=9 p.mode=air p.kind=pax",
            pre + "V216_SELECT seq=1 path=build budget=100 k_dec=0 probe_ops=7",
            pre + "V216_DECOMP seq=2 role=ranked rank=0 key=air|2 finance=20 affordable=1 tier=0 select_score=60 fund_profit=5 p.mode=air p.kind=pax",
            pre + "V216_DECOMP seq=2 role=ranked rank=4 key=rail|1 finance=80 affordable=1 tier=0 select_score=40 fund_profit=30 p.mode=rail p.kind=pax c.carried=12",
            pre + "V216_DECOMP seq=2 role=unaffordable rank=0 key=air|3 finance=900 affordable=0 tier=0 select_score=99 fund_profit=90 p.mode=air p.kind=pax",
            pre + "V216_SELECT seq=2 path=reselect budget=100 k_dec=50 probe_ops=11",
            pre + "V216_DECOMP seq=3 role=built_pax rank=0 key=rail|1 finance=80 affordable=1 p.mode=rail p.kind=pax",
            "noise line",
        ]
        with tempfile.NamedTemporaryFile("w", suffix=".log", delete=False) as fh:
            fh.write("\n".join(lines) + "\n")
        game = a.parse_log(fh.name)
        Path(fh.name).unlink()
        sel, built, rail, top, air, unaff = a.first_rail_pax_choice(game)
        self.assertEqual(sel["path"], "reselect")
        self.assertEqual(built["key"], "rail|1")
        self.assertEqual(rail["rank"], 4)
        self.assertEqual(top["key"], "air|2")
        self.assertEqual(air["key"], "air|2")
        self.assertEqual(unaff["key"], "air|3")
        wins = a.kdec_wins([game])
        self.assertEqual(wins["air"], (1, 3))
        self.assertEqual(wins["rail"], (0, 1))

    def test_join_rail_lines(self):
        import sys
        sys.path.insert(0, str(Path(__file__).resolve().parent))
        import analyze_v216 as a
        game = {
            'built': [
                {'role': 'built_freight', 'p.src': 100, 'p.dst': 200, 'p.revenueAnnual': 5000, 'key': 'rail|100|200|COAL|freight'},
                {'role': 'built_pax', 'p.src': 300, 'p.dst': 400, 'p.revenueAnnual': 8000, 'key': 'rail|300|400|PASS|pax'},
            ],
            'rail_build': [
                {'line': 11, 'src': 100, 'dst': 200, 'cargo': 'COAL', 'date': '1971-1-15'},
                {'line': 12, 'src': 300, 'dst': 400, 'cargo': 'PASS', 'date': '1971-6-1'},
            ]
        }
        joined = a.join_rail_lines(game)
        self.assertEqual(len(joined), 2)
        self.assertEqual(joined[11]['line'], 11)
        self.assertEqual(joined[11]['decomp']['p.revenueAnnual'], 5000)
        self.assertEqual(joined[12]['line'], 12)
        self.assertEqual(joined[12]['decomp']['p.revenueAnnual'], 8000)

    def test_error_attribution_b(self):
        import sys
        sys.path.insert(0, str(Path(__file__).resolve().parent))
        import analyze_v216 as a
        # Line 1: built 1971-1-11 (355 days >= 180). Line 2: built 1971-10-1 (< 180 days -> excluded).
        game = {
            'rail_build': [
                {'line': 1, 'src': 10, 'dst': 20, 'cargo': 'COAL', 'trains': 1, 'date': '1971-1-11'},
                {'line': 2, 'src': 30, 'dst': 40, 'cargo': 'PASS', 'trains': 1, 'date': '1971-10-1'},
            ],
            'built': [
                {'role': 'built_freight', 'p.src': 10, 'p.dst': 20, 'c.offered': 70.0,
                 'c.monthlyCapacity': 100.0, 'c.oneWayDays': 10.0, 'dwell_station_days': 5.0},
                {'role': 'built_pax', 'p.src': 30, 'p.dst': 40, 'c.offered': 50.0,
                 'c.monthlyCapacity': 50.0, 'c.oneWayDays': 10.0, 'dwell_station_days': 0.0},
            ],
            'line_revenue': [
                {'line': 1, 'year': 1972, 'pred_rev': 10000, 'real_rev': 8000,
                 'pred_prof': 8000, 'real_prof': 6000, 'pred_run': 2000, 'real_run': 2000, 'vehs': 1},
                {'line': 2, 'year': 1972, 'pred_rev': 5000, 'real_rev': 4000,
                 'pred_prof': 4000, 'real_prof': 3000, 'pred_run': 1000, 'real_run': 1000, 'vehs': 1},
            ]
        }
        game['rail_joins'] = a.join_rail_lines(game)
        res = a.error_attribution_b([game])
        self.assertIn('freight', res)
        self.assertNotIn('PASS', res)  # line 2 has < 180 days, excluded
        f = res['freight']
        self.assertEqual(f['n'], 1)
        # Check dwell-corrected capacity:
        # rt = 2 * 10 = 20, denom = 20 + 2*5 = 30 -> corr = 100 * 20/30 = 66.67
        self.assertAlmostEqual(f['mean_corr_capacity'], 100.0 * 20.0 / 30.0, places=1)
        # Uncorrected: offered=70 <= cap=100 -> offered binds
        # Corrected: cap=66.67 < offered=70 -> capacity binds
        self.assertEqual(f['uncorr_binds'], {'offered': 1})
        self.assertEqual(f['corr_binds'], {'capacity': 1})

    def test_invariance_test_d(self):
        import sys
        sys.path.insert(0, str(Path(__file__).resolve().parent))
        import analyze_v216 as a

        def make_game(pred, real, gain_pct, line_pct):
            return {
                'rail_build': [{'line': 1, 'src': 1, 'dst': 2, 'cargo': 'PASS', 'trains': 1, 'date': '1971-1-1'}],
                'built': [{'role': 'built_pax', 'p.src': 1, 'p.dst': 2,
                           'g.a_gain_pct': gain_pct, 'g.b_gain_pct': gain_pct,
                           'g.a_line_pct': line_pct, 'g.b_line_pct': line_pct}],
                'line_revenue': [{'line': 1, 'year': 1972, 'pred_rev': pred, 'real_rev': real,
                                  'pred_prof': pred, 'real_prof': real, 'pred_run': 0, 'real_run': 0, 'vehs': 1}],
            }

        # Passing case: cells have ratios around 1.0 (in [0.7, 1.4], spread <= 1.5)
        # cell1: pred=100, real=100, ghost_gain=100% -> ghost_pred=100 -> ratio=1.0
        # cell2: pred=100, real=110, ghost_gain=100% -> ghost_pred=100 -> ratio=1.1
        c1 = make_game(100, 100, 100, 100)
        c2 = make_game(100, 110, 100, 100)
        c1['rail_joins'] = a.join_rail_lines(c1)
        c2['rail_joins'] = a.join_rail_lines(c2)
        res_pass = a.invariance_test_d({'cellA': [c1], 'cellB': [c2]})
        self.assertEqual(res_pass['verdict'], 'PASS')
        self.assertAlmostEqual(res_pass['min_ratio'], 1.0, places=2)
        self.assertAlmostEqual(res_pass['max_ratio'], 1.1, places=2)

        # Failing case: ratio outside [0.7, 1.4]
        c_fail = make_game(100, 50, 100, 100)  # ratio = 0.5 < 0.7
        c_fail['rail_joins'] = a.join_rail_lines(c_fail)
        res_fail = a.invariance_test_d({'cellA': [c_fail]})
        self.assertEqual(res_fail['verdict'], 'FAIL')

    def test_replay_selections_6(self):
        import sys
        sys.path.insert(0, str(Path(__file__).resolve().parent))
        import analyze_v216 as a

        # Selection where original rank 0 is rail/pax, but ghost gain degrades it below air/pax
        game = {
            'select': {1: {'date': '1971-4-1'}},
            'decomp': {
                1: [
                    {'role': 'ranked', 'rank': 0, 'key': 'rail|1', 'affordable': 1, 'tier': 0,
                     'select_score': 200, 'fund_profit': 100, 'p.mode': 'rail', 'p.kind': 'pax',
                     'g.a_gain_pct': 20, 'g.b_gain_pct': 20},  # rescaled profit = 20, score = 40
                    {'role': 'ranked', 'rank': 1, 'key': 'air|1', 'affordable': 1, 'tier': 0,
                     'select_score': 100, 'fund_profit': 50, 'p.mode': 'air', 'p.kind': 'pax'},
                ]
            }
        }
        res = a.replay_selections_6([game])
        self.assertEqual(res['total_selections'], 1)
        self.assertEqual(res['changed_selections'], 1)
        self.assertEqual(res['changed_1971_1972'], 1)
        self.assertIn(('rail/pax', 'air/pax'), res['replacements'])

        # Test admission rejection when rescaled profit <= 0
        game_reject = {
            'select': {1: {'date': '1971-5-1'}},
            'decomp': {
                1: [
                    {'role': 'ranked', 'rank': 0, 'key': 'rail|pax', 'affordable': 1, 'tier': 0,
                     'select_score': 100, 'fund_profit': 50, 'p.mode': 'rail', 'p.kind': 'pax',
                     'g.a_gain_pct': 0, 'g.b_gain_pct': 0},  # profit <= 0 -> dropped!
                ]
            }
        }
        res_rej = a.replay_selections_6([game_reject])
        self.assertEqual(res_rej['changed_selections'], 1)
        self.assertIn(('rail/pax', 'none'), res_rej['replacements'])

    def test_competitor_arrival_g(self):
        import sys
        sys.path.insert(0, str(Path(__file__).resolve().parent))
        import analyze_v216 as a

        game = {
            'rail_build': [
                {'line': 1, 'cargo': 'COAL', 'src': 1, 'dst': 2, 'date': '1971-1-10'},
            ],
            'built': [
                {'role': 'built_freight', 'p.src': 1, 'p.dst': 2, 'p.cargo': 'COAL'},
            ],
            'ind_flow': [
                # Industry 10: initial stations 1, rises to 2 at month 8 (<= 12 mo)
                {'date': '1971-2-1', 'industry': 10, 'cargo': 'COAL', 'stations_around': 1},
                {'date': '1971-8-1', 'industry': 10, 'cargo': 'COAL', 'stations_around': 2},
                # Industry 20: initial stations 1, stays 1
                {'date': '1971-2-1', 'industry': 20, 'cargo': 'COAL', 'stations_around': 1},
                {'date': '1972-1-1', 'industry': 20, 'cargo': 'COAL', 'stations_around': 1},
            ]
        }
        game['rail_joins'] = a.join_rail_lines(game)
        res = a.competitor_arrival_g([game])
        self.assertEqual(res['total_industries'], 2)
        self.assertEqual(res['arrived_count'], 1)
        self.assertAlmostEqual(res['share'], 0.5)

    def test_parse_cli_args(self):
        import sys
        sys.path.insert(0, str(Path(__file__).resolve().parent))
        import analyze_v216 as a

        # Backward compatibility format
        self.assertEqual(a.parse_cli_args(['engine_dir', 'pol1', 'pol2']),
                         [('engine_dir', ['pol1', 'pol2'])])
        # Multi-dir format with colon
        self.assertEqual(a.parse_cli_args(['dirA:p1,p2', 'dirB:p3']),
                         [('dirA', ['p1', 'p2']), ('dirB', ['p3'])])
        # Single dir default policies
        self.assertEqual(a.parse_cli_args(['dirA']),
                         [('dirA', ['ref', 'probe'])])


if __name__ == "__main__":
    unittest.main()
