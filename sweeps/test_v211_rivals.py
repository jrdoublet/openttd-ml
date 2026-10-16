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


if __name__ == "__main__":
    unittest.main()
