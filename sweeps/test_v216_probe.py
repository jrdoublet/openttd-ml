"""V216 etape 1 : contrats statiques de la sonde passive des estimateurs.

docs/plan_v216_scores_avant_premier_rail_20261016.md section 3.5 : reglage declare a 0,
lu une seule fois, aucun appel hors `if (V216_PROBE`, et la sonde ne commande rien au jeu.
Ce n'est pas un test de VM NoAI ; le smoke 1x1 sur 3 ans complete ces contrats.
"""
from pathlib import Path
import re
import unittest


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

    def test_setting_declared_inert(self):
        block = re.search(r'name = "v216_probe",(.*?)\}\);', self.info, re.S)
        self.assertIsNotNone(block)
        for level in ("easy_value", "medium_value", "hard_value", "custom_value"):
            self.assertRegex(block.group(1), level + r" = 0\b")
        self.assertIn("CONFIG_BOOLEAN", block.group(1))

    def test_setting_read_once(self):
        self.assertEqual(self.settings.count('GetSetting("v216_probe")'), 1)
        self.assertEqual(sum(s.count('GetSetting("v216_probe")') for s in self.sources.values()), 1)
        self.assertIn("V216_PROBE <- false;", self.sources["globals_pre.nut"])

    def test_probe_is_required(self):
        self.assertIn('require("probe_v216.nut");', self.sources["main.nut"])

    def test_every_call_site_is_guarded(self):
        hooks = 0
        for name, text in self.sources.items():
            for line in text.splitlines():
                if re.search(r"\bOpexV216\w*\(|\bV216_(?!PROBE\b)\w+\s*=", line):
                    hooks += 1
                    self.assertRegex(line, r"if \(V216_PROBE\b", name + ": " + line.strip())
        # selection x3, K_dec, rejets x3, RAIL_BUILD, tick mensuel
        self.assertEqual(hooks, 9)

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


if __name__ == "__main__":
    unittest.main()
