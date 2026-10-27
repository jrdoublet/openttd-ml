"""ESTIM-1 bits 1/2/4/8 : contrats de source OFF exacte (HEAD) et lot 1."""
import re
import subprocess
import unittest
from pathlib import Path

from estim_unifie_legacy import EDITS, estim_off, estim_off_bytes
from estim_unifie_off_lots import ESTIM_FILES
from test_v261_forum_behaviours import body, source

ROOT = Path(__file__).resolve().parents[1]


def head_source(name):
    try:
        return subprocess.run(["git", "show", "HEAD:ai/OpexAI/" + name], cwd=ROOT,
                              capture_output=True, check=True).stdout.decode("utf-8")
    except (OSError, subprocess.CalledProcessError):
        return None


def head_bytes(name):
    try:
        return subprocess.run(["git", "show", "HEAD:ai/OpexAI/" + name], cwd=ROOT,
                              capture_output=True, check=True).stdout
    except (OSError, subprocess.CalledProcessError):
        return None


def shrink(real, pred, n, prior, w0=10.0):
    return prior if n <= 0 or pred <= 0 else (n * real / pred + w0 * prior) / (n + w0)


class EstimUnifieContracts(unittest.TestCase):
    def test_setting_default_zero_everywhere_and_single_read(self):
        block = re.search(r'AddSetting\(\{\s*name = "estim_unifie",.*?\}\);', source("info.nut"), re.S)[0]
        self.assertIn("min_value = 0, max_value = 15", block)
        for level in ("easy", "medium", "hard", "custom", "default"):
            self.assertRegex(block, level + r"_value\s*=\s*0\b")
        self.assertEqual(source("settings.nut").count('GetSetting("estim_unifie")'), 1)
        self.assertIn("ESTIM_UNIFIE <- 0;", source("globals_pre.nut"))

    def test_binding_follows_historical_binding(self):
        settings = source("settings.nut")
        hist = settings.index("::OpexCalibratedProfit <- OpexC70Profit;")
        self.assertLess(settings.index('GetSetting("estim_unifie")'), hist)
        self.assertLess(hist, settings.index("::OpexCalibratedProfit <- OpexEstimProfit;"))
        self.assertIn("if ((ESTIM_UNIFIE & 1) != 0) ::OpexCalibratedProfit <- OpexEstimProfit;", settings)
        # Nouvelle partie : facteurs remis a l'a priori a chaque chargement des reglages.
        self.assertIn("foreach (m, k in ESTIM_K_R_PRIOR) ESTIM_K_R[m] = k;", settings)

    def test_off_projection_restores_head_bytes(self):
        self.assertEqual(set(EDITS), ESTIM_FILES)
        for name in EDITS:
            head = head_bytes(name)
            if head is None:
                self.fail("git HEAD indisponible : projection non verifiable")
            current = (ROOT / "ai" / "OpexAI" / name).read_bytes()
            with self.subTest(name=name):
                self.assertEqual(estim_off_bytes(name, current), head)
                # Une projection deja effectuee est un no-op strict.
                self.assertEqual(estim_off_bytes(name, head), head)
        # Hors ESTIM, les modifications d'origine restent en place. Les deux
        # reglages dist_bornes figuraient deja dans HEAD avant le lot ESTIM.
        for name in ("info.nut", "settings.nut"):
            with self.subTest(preserve=name):
                extra = "/* autre modification deja presente */\n"
                self.assertEqual(estim_off(name, extra + source(name)),
                                 extra + head_source(name))
                self.assertIn("dist_bornes_unified", head_source(name))
        self.assertEqual(estim_off("unknown.nut", "non-ESTIM edit"), "non-ESTIM edit")
        with self.assertRaises(AssertionError):
            estim_off("task_report.nut", source("task_report.nut").replace(
                "if (estimRevSums != null) OpexEstimAccumulateLine", "if (true) OpexEstimAccumulateLine"))

    def test_each_opt_in_bit_has_source_coverage(self):
        files = {name: source(name) for name in EDITS}
        for bit in (1, 2, 4, 8):
            with self.subTest(bit=bit):
                self.assertTrue(any(re.search(r"ESTIM_UNIFIE\s*&\s*" + str(bit) + r"\b", src)
                                    for src in files.values()))
        self.assertIn("OpexEstimMonthDays", files["air_economics_c121.nut"])
        self.assertIn("OpexEstimFinanceCapital", files["projects_finance.nut"])
        self.assertIn("OpexEstimProjectFromFleet", files["projects_builders.nut"])
        self.assertIn("OpexEstimV284Project", files["task_v284.nut"])

    def test_air_factor_guard_is_first_and_bit_gated(self):
        fn = body("projects_models.nut", "OpexC121RealizationFactor")
        code = [l.strip() for l in fn.splitlines() if l.strip() and not l.strip().startswith(("/*", "*"))]
        self.assertEqual(code[1], "if ((ESTIM_UNIFIE & 1) != 0) return ESTIM_K_R.air;")

    def test_profit_corrects_revenue_not_profit(self):
        fn = body("projects_models.nut", "OpexEstimProfit")
        self.assertIn("project.profitAnnual - (1.0 - ESTIM_K_R[project.mode]) * project.revenueAnnual", fn)
        # AIR C121 porte deja k_R dans l'economie : pas de double correction.
        self.assertIn('project.mode == "air" && OpexC121ProjectHasRealization(project)', fn)
        # Observations, flotte (mode absent de ESTIM_K_R) et projets sans recette : historique.
        self.assertIn("profitIsObserved", fn)
        self.assertEqual(fn.count("return OpexC70Profit(project);"), 1)
        self.assertNotIn("fleet", re.sub(r"/\*.*?\*/", "", source("globals_pre.nut").split("ESTIM_K_R <-")[1].split("\n")[0]))

    def test_learning_sample_contract(self):
        fn = body("projects_models.nut", "OpexEstimAccumulateLine")
        self.assertIn("age >= 2 && n0 > 0 && vehCount == n0 && pred > 0", fn)
        # Sans recette brute du shadow, predRevenue AIR est DEJA calibre :
        # sa reutilisation en denominateur tirerait l'apprentissage vers 1.
        self.assertIn('mode == "air" && (!("c121RawRevenueAnnual" in line)', fn)
        self.assertIn('mode == "air" ? line.c121RawRevenueAnnual', fn)
        self.assertNotIn("/ vehCount", fn)  # aucune normalisation lineaire par la flotte
        report = source("task_report.nut")
        self.assertIn("local estimRevSums = (ESTIM_UNIFIE & 1) != 0 ? OpexEstimRevenueSums() : null;", report)
        self.assertLess(report.index("OpexEstimAccumulateLine"), report.index("line.vehCount <- vehCount;"))
        self.assertLess(report.index('OpexC121ApplyRealizationSums(c121RealizationSums, year, "annual")'),
                        report.index('OpexEstimPublishRevenueFactors(estimRevSums, year, "annual")'))

    def test_reload_recomputes_after_lines_restored(self):
        persist = source("persist.nut")
        restored = persist.index("this._lines = liveLines;")
        call = persist.index("OpexEstimRecomputeRevenueFactors(this._lines);")
        self.assertLess(restored, call)
        self.assertLess(persist.index("OpexC121RecomputeRealizationFactors(this._lines);"), call)
        # Cumuls entiers : la sauvegarde arrondit les flottants sans biaiser le rapport.
        acc = body("projects_models.nut", "OpexEstimAccumulateLine")
        self.assertIn("line.estimRevReal <- 0; line.estimRevPred <- 0; line.estimRevN <- 0;", acc)
        self.assertIn("pred.tointeger()", acc)

    def test_air_change_invalidates_catalogue_cache(self):
        fn = body("projects_models.nut", "OpexEstimPublishRevenueFactors")
        self.assertIn('if (m == "air" && changed)', fn)
        self.assertIn("C121_CATALOG_ARM_LEARN_REV.rawset(arm", fn)
        self.assertIn('if (m == "air" && changed) airChanged = true;', fn)
        self.assertIn("return airChanged;", fn)
        for arm in ("newpair", "hubsite", "hubhub"):
            self.assertIn('"' + arm + '"', fn)
        # La revision C121 ne re-evalue pas les projets deja presents dans
        # _projects : demander un nouveau vivier au prochain passage catalogue.
        report = source("task_report.nut")
        self.assertIn('if (estimRevSums != null && OpexEstimPublishRevenueFactors(estimRevSums, year, "annual"))', report)
        self.assertIn("this._portfolioInvalidated = true;", report)

    def test_shrinkage_formula(self):
        fn = body("projects_models.nut", "OpexEstimPublishRevenueFactors")
        self.assertIn("k = (n * acc[0] / acc[1] + w0 * k) / (n + w0);", fn)
        self.assertAlmostEqual(shrink(0, 0, 0, 0.40), 0.40)
        self.assertAlmostEqual(shrink(500, 1000, 10, 0.40), 0.45)
        self.assertAlmostEqual(shrink(500, 1000, 1000, 0.40), (1000 * 0.5 + 4) / 1010)

    def test_priors_match_corpus_rounding(self):
        globals_pre = source("globals_pre.nut")
        prior = "ESTIM_K_R_PRIOR <- { rail = 0.92, road = 0.57, air = 0.40, water = 1.0 };"
        self.assertIn(prior, globals_pre)
        self.assertIn(prior.replace("ESTIM_K_R_PRIOR", "ESTIM_K_R"), globals_pre)
        self.assertIn("ESTIM_K_R_PRIOR_WEIGHT <- 10.0;", globals_pre)


if __name__ == "__main__":
    unittest.main()
