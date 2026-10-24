"""AIR-ROI-LIGNE-1: publication boundaries, not a Squirrel/runtime test."""
import hashlib
import re
import unittest
from pathlib import Path

AI = Path(__file__).resolve().parents[1] / "ai" / "OpexAI"


def read(name):
    return (AI / name).read_text(encoding="utf-8")


def body(name, function):
    # Production functions start at column zero; preserve nested blocks.
    return read(name).split("function " + function + "(", 1)[1].split("\n}", 1)[0]


class AirProfitCalibrationContracts(unittest.TestCase):
    def test_setting_and_single_load(self):
        setting = read("info.nut").split('name = "air_profit_cal_pct"', 1)[1].split("});", 1)[0]
        for field, value in (("min_value", 10), ("max_value", 200), ("step_size", 5),
                             ("easy_value", 100), ("medium_value", 100),
                             ("hard_value", 100), ("custom_value", 100)):
            self.assertRegex(setting, rf"\b{field}\s*=\s*{value}\b")
        self.assertIn("AIR_PROFIT_CAL_PCT <- 100;", read("globals_pre.nut"))
        all_code = "\n".join(p.read_text(encoding="utf-8") for p in AI.glob("*.nut"))
        self.assertEqual(all_code.count('GetSetting("air_profit_cal_pct")'), 1)
        self.assertIn("AIR_PROFIT_CAL_PCT = 100;", read("settings.nut"))
        self.assertIn('DECISION_LOG = (probes & 508) != 0;', read("settings.nut"))
        self.assertEqual(508 & 256, 256)

    def test_identity_precedes_mutation_and_other_modes_excluded(self):
        code = body("projects_models.nut", "OpexAirCalibrateInvestment")
        self.assertLess(code.index("if (AIR_PROFIT_CAL_PCT == 100) return;"),
                        code.index("local factor"))
        self.assertIn('if (project.mode != "air" && project.mode != "fleet") return;', code)
        mutations = re.findall(r"project\.(\w+)\s*\*=", code)
        self.assertEqual(mutations, ["profitAnnual", "roi"])
        self.assertNotIn("tointeger", code)  # positive sub-pound forecasts stay positive

    def test_actual_factor_expression_and_no_truncation(self):
        code = body("projects_models.nut", "OpexAirCalibrateInvestment")
        expression = re.search(r"local factor = ([^;]+);", code).group(1)
        self.assertEqual(expression, "AIR_PROFIT_CAL_PCT / 100.0")
        for pct in (10, 80, 100, 200):
            factor = eval(expression, {"__builtins__": {}}, {"AIR_PROFIT_CAL_PCT": pct})
            for profit in (0.01, 1, 13000, 100000000, -13):
                self.assertAlmostEqual(profit * factor, profit * pct / 100)
        self.assertIn("project.profitAnnual *= factor;", code)
        self.assertIn("project.roi *= factor;", code)

    def test_exactly_two_publication_calls_no_second_factor(self):
        sites = []
        for path in AI.glob("*.nut"):
            for line in path.read_text(encoding="utf-8").splitlines():
                if "OpexAirCalibrateInvestment(" in line and not line.startswith("function "):
                    sites.append((path.name, line.strip()))
        self.assertEqual(sites, [("projects_builders.nut", "OpexAirCalibrateInvestment(project);")] * 2)
        for function in ("OpexProjectFromAir", "OpexProjectFromFleet"):
            code = body("projects_builders.nut", function)
            self.assertEqual(code.count("OpexAirCalibrateInvestment(project);"), 1)
            self.assertRegex(code, r"OpexAirCalibrateInvestment\(project\);\s*return project;")
        self.assertNotIn("AIR_PROFIT_CAL_PCT", body("projects_models.nut", "OpexC70Profit"))
        self.assertNotIn("CalibrateInvestment", read("projects_update.nut"))
        self.assertNotIn("CalibrateInvestment", read("projects_selection.nut"))

    def test_all_new_air_arms_use_common_constructor(self):
        code = body("projects_builders.nut", "OpexProjectFromAir")
        self.assertNotIn('plan.arm', code)  # no newpair/hubsite/hubhub exemption
        self.assertIn("profitAnnual = decisionEconomics.profitAnnual", code)
        self.assertIn("? plan.decisionEconomics : economics", code)
        for name in ("projects.nut", "projects_update.nut", "projects_generation.nut", "po01c_regen.nut"):
            catalog = "s.catalog" if name == "po01c_regen.nut" else "catalog"
            self.assertIn("OpexProjectFromAir(" + catalog + ", plan,", read(name))
        constructors = []
        for path in AI.glob("*.nut"):
            if re.search(r'mode = "air", kind = "pax"', path.read_text(encoding="utf-8")):
                constructors.append(path.name)
        self.assertEqual(constructors, ["projects_builders.nut"])

    def test_all_fleet_sources_after_v161_including_observed_prior(self):
        code = body("projects_builders.nut", "OpexProjectFromFleet")
        calibration = code.index("OpexAirCalibrateInvestment(project);")
        for term in ("line.c121MarginalProfit", "line.lastProfit / have",
                     "(line.predRevenue - running) / planes", "OpexV161PerPlaneProfit(",
                     'profitIsObserved = v161Source != "model"', "project.v161Calibrate <- true"):
            self.assertLess(code.index(term), calibration)
        self.assertIn("OpexProjectFromFleet(entry)", read("po01c_regen.nut"))
        self.assertIn("OpexProjectFromFleet(entry)", read("projects_update.nut"))
        # Resizing receives the calibrated project, never a new model calculation.
        fit = body("projects_selection.nut", "OpexProjectFitFleetToBudget")
        self.assertIn("local fitted = clone project;", fit)
        self.assertIn("(project.profitAnnual / entry.want) * quantity", fit)
        self.assertNotIn("AIR_PROFIT_CAL_PCT", fit)

    def test_admission_guards_and_finance(self):
        code = body("projects_selection.nut", "OpexProjectSelectAffordable")
        self.assertEqual(re.findall(r"floorProfit\s*=\s*([^;]+);", code), ["0"])
        self.assertIn("OpexProjectFundProfit(project)", code)
        self.assertIn("OpexCalibratedProfit(project)", body("projects_selection.nut", "OpexProjectFundProfit"))
        margin = body("projects_builders.nut", "OpexAirRequiredMargin")
        self.assertIn("30000", margin)
        self.assertIn("12000", margin)
        self.assertIn("2000", margin)
        self.assertNotIn("profit", margin.lower())
        self.assertNotIn("AIR_PROFIT_CAL_PCT", read("projects_finance.nut"))

    def test_choice_logs_include_cal_and_use_investment_profit(self):
        for name, event in (("task_air.nut", "PROJECT_CHOSEN"),
                            ("task_projects.nut", "FLEET_PROJECT"),
                            ("projects_rank_log.nut", "PORTFOLIO_RANK")):
            code = read(name)
            logs = re.findall(r'OpexDecide\("' + event + r'".*?;', code, re.S)
            self.assertTrue(logs)
            for log in logs:
                self.assertIn("cal=", log)
                self.assertIn("AIR_PROFIT_CAL_PCT", log)
            self.assertIn("DECISION_LOG", code)
        chosen = re.search(r'OpexDecide\("PROJECT_CHOSEN".*?;', read("task_air.nut"), re.S).group()
        self.assertIn('" profit=" + project.profitAnnual', chosen)

    def test_raw_models_and_realized_accounting_unchanged(self):
        # Pins established on c03fce93 (initial branch). Calibration must stay at
        # publication, otherwise C121 marginal differences / C70 learning may
        # ingest the factor twice or cancel it through their learned ratios.
        expected = RAW_HASHES
        for name, digest in expected.items():
            with self.subTest(name=name):
                self.assertEqual(hashlib.sha256((AI / name).read_bytes()).hexdigest(), digest)


RAW_HASHES = {
    'air_route_economics.nut': 'a814d123ebc737c450fded043bf15dfac89624f93fb347327f0f28e9588b772d',
    'air_economics_c121.nut': '1064d7670510c77f4bda08bac28d92a70a9bb81d17e7f1c5abfd0a85817d3aed',
    'air_catalog_c121.nut': 'e121dcd336d814526348dbad901bdacad81619a0fe2014a83a3c600b2fe1ed28',
    'air_fleet.nut': '487e037801834ce050ea67349e076c8b9878340babff6ce1579b379b23672d39',
    'task_report.nut': '6a2bbb94a821db6f958ae7500a26e5c89ae2d6317201ed1f13524bfac9bf6fec',
    'persist.nut': 'd04be54e9baf6e58dc49d5410149b85ad31fb00a28c17f408f79591d559210df',
    'task_v252.nut': '851f3762ddbc296066c49cbe56eb82a686b31f25eaa6c40484c9ddd1bedc3ea6',
}
