"""V211 : contrats statiques du releve trimestriel des concurrents.

Reglage declare a 0, lu une seule fois, un seul appel garde par `if (V211_RIVALS)`, et le module
ne commande rien au jeu ni ne nourrit aucune decision. Le smoke 1x1 complete ces contrats.
"""
from pathlib import Path
import re
import unittest


AI = Path(__file__).resolve().parents[1] / "ai" / "OpexAI"
MODULE = AI / "rivals_v211.nut"


class TestV211Rivals(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.info = (AI / "info.nut").read_text(encoding="utf-8")
        cls.module = MODULE.read_text(encoding="utf-8")
        cls.sources = {p.name: p.read_text(encoding="utf-8")
                       for p in AI.glob("*.nut") if p.name != MODULE.name}

    def test_setting_declared_inert(self):
        block = re.search(r'name = "v211_rivals_log",(.*?)\}\);', self.info, re.S)
        self.assertIsNotNone(block)
        for level in ("easy_value", "medium_value", "hard_value", "custom_value"):
            self.assertRegex(block.group(1), level + r" = 0\b")
        self.assertIn("CONFIG_BOOLEAN", block.group(1))

    def test_setting_read_once(self):
        self.assertEqual(sum(s.count('GetSetting("v211_rivals_log")') for s in self.sources.values()), 1)
        self.assertIn("V211_RIVALS <- false;", self.sources["globals_pre.nut"])
        self.assertIn('require("rivals_v211.nut");', self.sources["main.nut"])

    def test_single_guarded_hook(self):
        hooks = [(n, l) for n, t in self.sources.items() for l in t.splitlines()
                 if re.search(r"\bOpexV211\w*\(", l)]
        self.assertEqual(len(hooks), 1, hooks)
        self.assertRegex(hooks[0][1], r"if \(V211_RIVALS\) OpexV211QuarterlyTick\(\);")

    def test_never_commands_the_game(self):
        code = re.sub(r"/\*.*?\*/", "", self.module, flags=re.S)
        calls = set(re.findall(r"\bAI\w+\.(\w+)\(", code))
        forbidden = [c for c in calls
                     if re.match(r"(Build|Remove|Demolish|Set|Sell|Clone|Start|Stop|Skip|Send|"
                                 r"Append|Insert|Delete|Change|Refit|Found|Fund|Buy|Pay)", c)]
        self.assertEqual(forbidden, [])
        # Aucune autre source ne lit ce que le module calcule.
        for name, text in self.sources.items():
            if name == "globals_pre.nut":
                continue
            self.assertNotRegex(text, r"\bV211_LAST_QUARTER\b", name)

    def test_quarter_index(self):
        self.assertIn("(AIDate.GetMonth(now) - 1) / 3", self.module)

    def test_self_score_components(self):
        self.assertIn('OpexDecide("V211_SCORE"', self.module)
        for part in ("vehicles", "stations", "min_profit", "min_income", "max_income",
                     "delivered", "cargo", "money", "loan_margin"):
            self.assertIn('["' + part + '"', self.module)
        # Total des points = 1000, comme la note d'OpenTTD.
        pts = re.findall(r'\["\w+", [^,]+, \d+, (\d+)\]', self.module)
        self.assertEqual(sum(int(p) for p in pts), 1000)


class TestAnalyzeV211(unittest.TestCase):
    def test_parse_and_overtake(self):
        import sys, tempfile
        sys.path.insert(0, str(Path(__file__).resolve().parent))
        import analyze_v211 as a
        pre = "[t] dbg: [script:4] [0] [I] OPEX "
        def row(date, c, me, value, perf):
            return (pre + f"{date} V211_RIVAL company={c} self={me} name=X value={value} perf={perf} "
                    f"income=10 expenses=-5 profit=5 delivered=3 bank=7 rail=1 road=2 stations=3 airports=4 canals=0")
        lines = [row("1970-4-1", 0, 1, 100, 50), row("1970-4-1", 1, 0, 50, 60),
                 row("1970-7-1", 0, 1, 100, 50), row("1970-7-1", 1, 0, 150, 40),
                 row("1971-1-1", 0, 1, 100, 50), row("1971-1-1", 1, 0, 150, 60), "noise"]
        with tempfile.NamedTemporaryFile("w", suffix=".log", delete=False) as fh:
            fh.write("\n".join(lines) + "\n")
        game = a.parse_log(fh.name)
        Path(fh.name).unlink()
        self.assertEqual(sorted(game), [1970 * 4, 1970 * 4 + 1, 1970 * 4 + 3])
        self.assertEqual(a.overtaken_from(game, "value"), 1970 * 4 + 1)
        self.assertEqual(a.overtaken_from(game, "perf"), 1970 * 4 + 3)
        acc = a.year_table([game])
        self.assertEqual(acc[1970]["lead_value"], [1, 0, 0])
        self.assertEqual(a.fmt_q(1970 * 4 + 3), "1970-T4")

    def test_parse_scores(self):
        import sys, tempfile
        sys.path.insert(0, str(Path(__file__).resolve().parent))
        import analyze_v211 as a
        pre = "[t] dbg: [script:4] [0] [I] OPEX "
        lines = [pre + "1972-4-1 V211_SCORE perf=600 vehicles=57 pts_vehicles=47/100 cargo=2 pts_cargo=12/50 total=59 ops=1",
                 pre + "1973-1-1 V211_SCORE perf=650 vehicles=60 pts_vehicles=50/100 total=50 ops=1"]
        with tempfile.NamedTemporaryFile("w", suffix=".log", delete=False) as fh:
            fh.write("\n".join(lines) + "\n")
        rows = a.parse_scores(fh.name)
        Path(fh.name).unlink()
        self.assertEqual(rows[0][0], 1972)
        self.assertEqual(rows[0][1]["vehicles"], (47, 100))
        self.assertEqual(rows[1][0], 1972)  # janvier 1973 = trimestre clos de 1972
        acc = a.score_table([rows])
        self.assertEqual(acc[1972]["vehicles"], [47])  # le releve de janvier est ecarte


if __name__ == "__main__":
    unittest.main()
