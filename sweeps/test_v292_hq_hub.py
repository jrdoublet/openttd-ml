"""V292b : tests statiques du placement unique et gratuit du QG pres du hub voyageurs.

Reglage v292_hq_hub (0/1, defaut 0, lu une seule fois). A 0, code strictement inerte.
A 1, au passage mensuel existant (repay), si aucun QG n'est pose et qu'une gare
voyageurs existe, pose le QG dans son rayon de captage pres de la gare la plus
chargee, sans jamais demenager le QG. Borne a 64 essais et au plus 1 tentative par an.
"""
from pathlib import Path
import re
import unittest


AI = Path(__file__).resolve().parents[1] / "ai" / "OpexAI"


def _body(source, signature):
    match = re.search(re.escape(signature) + r"\n\{(.*?)\n\}", source, re.S)
    return match.group(1) if match else ""


class TestV292HqHub(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.sources = {p.name: p.read_text(encoding="utf-8") for p in AI.glob("*.nut")}
        cls.info = cls.sources["info.nut"]
        cls.settings = cls.sources["settings.nut"]
        cls.globals_pre = cls.sources["globals_pre.nut"]
        cls.main = cls.sources["main.nut"]
        cls.report = cls.sources["task_report.nut"]
        cls.sched_tasks = cls.sources["scheduler_tasks.nut"]
        cls.persist = cls.sources["persist.nut"]
        cls.hq_body = _body(cls.report, "function OpexAI::_v292TryBuildHq(year)")

    def test_setting_declared_default_one(self):
        block = re.search(r'AddSetting\(\{\s*name = "v292_hq_hub",(.*?)\}\);', self.info, re.S)
        self.assertIsNotNone(block, "v292_hq_hub doit etre declare dans info.nut")
        body = block.group(1)
        for level in ("easy_value", "medium_value", "hard_value", "custom_value"):
            self.assertRegex(body, rf"{level}\s*=\s*1\b")
        self.assertIn("min_value = 0, max_value = 1", body)
        self.assertIn("V292_HQ_HUB <- 1;", self.globals_pre)

    def test_setting_read_once(self):
        reads = [(name, text.count('GetSetting("v292_hq_hub")'))
                 for name, text in self.sources.items()]
        total_reads = sum(count for _, count in reads)
        self.assertEqual(total_reads, 1, "v292_hq_hub doit etre lu exactement une fois")
        self.assertIn('AIController.GetSetting("v292_hq_hub")', self.settings)
        self.assertIn("V292_HQ_HUB = (v292HqHub != null && v292HqHub == 1) ? 1 : 0;", self.settings)

    def test_guard_v292_hq_hub(self):
        self.assertTrue(self.hq_body, "_v292TryBuildHq doit etre defini dans task_report.nut")
        guard = "if (!V292_HQ_HUB) return;"
        self.assertIn(guard, self.hq_body)
        # Verifier que l'appel mensuel dans repay est garde par V292_HQ_HUB
        repay_body = _body(self.sched_tasks, "function OpexAI::_dispatchRepay(task, year)")
        self.assertIn("if (V292_HQ_HUB) this._v292TryBuildHq(year);", repay_body)

    def test_build_company_hq_present(self):
        self.assertIn("AICompany.BuildCompanyHQ", self.hq_body)

    def test_no_relocation(self):
        # Ne jamais demenager le QG : verification de GetCompanyHQ avant tout essai de pose
        check_hq = "local hqTile = AICompany.GetCompanyHQ(AICompany.COMPANY_SELF);"
        self.assertIn(check_hq, self.hq_body)
        self.assertIn("if (hqTile != null && AIMap.IsValidTile(hqTile)) return;", self.hq_body)
        # Position du check avant l'appel a BuildCompanyHQ
        idx_check = self.hq_body.index("AICompany.GetCompanyHQ")
        idx_build = self.hq_body.index("AICompany.BuildCompanyHQ")
        self.assertLess(idx_check, idx_build, "GetCompanyHQ doit etre verifie avant BuildCompanyHQ")
        # Arret au premier succes
        self.assertIn("if (AICompany.BuildCompanyHQ(cand.tile)) {\n      built = true;\n      builtTile = cand.tile;\n      break;\n    }", self.hq_body)

    def test_bounded_tries_and_yearly_retry(self):
        # Borne le nombre d'essais a 64
        self.assertIn("if (tries >= 64) break;", self.hq_body)
        # Reessayer au plus une fois par an en cas d'echec
        self.assertIn("if (this._v292LastHqTryYear >= 0 && year <= this._v292LastHqTryYear) return;", self.hq_body)
        self.assertIn("this._v292LastHqTryYear = year;", self.hq_body)

    def test_decision_log(self):
        self.assertIn('OpexDecide("V292_HQ"', self.hq_body)
        self.assertIn('"event=built station="', self.hq_body)
        self.assertIn('"event=fail station="', self.hq_body)

    def test_persistence(self):
        # Verification Save() et Load()
        self.assertIn("shortSave.v292LastHqTryYear <- this._v292LastHqTryYear;", self.persist)
        self.assertIn("saveObj.v292LastHqTryYear <- this._v292LastHqTryYear;", self.persist)
        self.assertIn('this._v292LastHqTryYear = ("v292LastHqTryYear" in data) ? data.v292LastHqTryYear : -1;', self.persist)
        self.assertIn("_v292LastHqTryYear = -1;", self.main)


if __name__ == "__main__":
    unittest.main()
