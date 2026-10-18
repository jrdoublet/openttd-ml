"""V229 : facteur C70 par cellule (mode, pax/fret, tranche de distance).

Contrats statiques. A defaut 0, le corps de OpexC70Factor et l'accumulation
par ligne restent ceux du facteur de mode.
"""
from pathlib import Path
import re
import unittest


AI = Path(__file__).resolve().parents[1] / "ai" / "OpexAI"
RESERVED = ("clone", "base", "parent")
NEW_FUNCTIONS = (
    "OpexC70CargoKind",
    "OpexC70Number",
    "OpexC70Median",
    "OpexC70CollectCellSamples",
    "OpexC70StoreCell",
    "OpexC70ApplyCells",
    "OpexC70CellFactor",
    "OpexC70FactorCells",
)


def source(name):
    return (AI / name).read_text(encoding="utf-8")


def squirrel_code(text):
    text = re.sub(r"/\*.*?\*/", "", text, flags=re.S)
    text = re.sub(r"//.*", "", text)
    return text


def function_body(src, signature):
    idx = src.index(signature)
    start = src.index("{", idx)
    depth = 0
    for i in range(start, len(src)):
        if src[i] == "{":
            depth += 1
        elif src[i] == "}":
            depth -= 1
            if depth == 0:
                return src[idx:i + 1]
    raise ValueError(signature)


class TestV229C70Cells(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.sources = {p.name: p.read_text(encoding="utf-8") for p in AI.glob("*.nut")}
        cls.models = cls.sources["projects_models.nut"]
        cls.report = cls.sources["task_report.nut"]
        cls.settings = cls.sources["settings.nut"]
        cls.info = cls.sources["info.nut"]
        cls.bodies = {
            name: function_body(cls.models, "function " + name + "(")
            for name in NEW_FUNCTIONS
        }

    def test_setting_declared_default_zero_and_read_once(self):
        block = re.search(
            r'name = "v229_c70_cells",(.*?)\}\);', self.info, re.S)
        self.assertIsNotNone(block)
        body = block.group(1)
        self.assertIn("flags = AICONFIG_BOOLEAN", body)
        for level in ("easy_value", "medium_value", "hard_value", "custom_value"):
            self.assertRegex(body, level + r" = 0\b")
        self.assertIn("V229_C70_CELLS <- false;", self.sources["globals_pre.nut"])
        self.assertIn("C70_CELL_FACTOR <- {};", self.sources["globals_pre.nut"])
        self.assertIn("C70_CELL_MEDIAN <- {};", self.sources["globals_pre.nut"])
        reads = [text.count('GetSetting("v229_c70_cells")') for text in self.sources.values()]
        self.assertEqual(sum(reads), 1)
        self.assertIn(
            'V229_C70_CELLS = AIController.GetSetting("v229_c70_cells") == 1;',
            self.settings)
        self.assertIn("if (V229_C70_CELLS) ::OpexC70Factor <- OpexC70FactorCells;", self.settings)

    def test_default_factor_and_accumulation_stay_on_the_mode_path(self):
        factor = function_body(self.models, "function OpexC70Factor(")
        self.assertNotIn("V229", factor)
        self.assertNotIn("C70_CELL", factor)
        self.assertIn('if (mode == "fleet")', factor)
        self.assertIn('mode = "air";', factor)
        self.assertIn(
            "return (mode in C70_MODE_FACTOR) ? C70_MODE_FACTOR[mode] : 1.0;",
            factor)
        accumulate = function_body(self.report, "function OpexC70C82AccumulateLine(")
        self.assertNotIn("V229", accumulate)
        self.assertNotIn("C70_CELL", accumulate)
        self.assertNotIn("CC_MAIL", accumulate)
        publish = function_body(self.report, "function OpexC70PublishModeFactors(")
        mode_log = publish.index('OpexC69Log("phase=c70_factor year=" + year + " mode=" + m')
        cell_call = publish.index("if (V229_C70_CELLS) OpexC70ApplyCells(lines, year);")
        self.assertLess(mode_log, cell_call)
        self.assertIn(
            "C70_MODE_FACTOR[m] = (acc[0] + 1.0) / (acc[1] + 1).tofloat();",
            publish)
        recompute = function_body(self.models, "function OpexC70RecomputeFactors(")
        self.assertIn(
            "C70_MODE_FACTOR[m] = (acc[0] + 1.0) / (acc[1] + 1).tofloat();",
            recompute)
        self.assertLess(
            recompute.index("C70_MODE_FACTOR[m] ="),
            recompute.index("if (V229_C70_CELLS) OpexC70ApplyCells(lines, null);"))
        self.assertNotIn("cargo", recompute.split("OpexC70ApplyCells", 1)[0])
        self.assertNotIn("distance", recompute.split("OpexC70ApplyCells", 1)[0])

    def test_cell_formula_median_and_shared_call(self):
        store = self.bodies["OpexC70StoreCell"]
        self.assertIn("(sumRatio + kMode) / (nCell + 1).tofloat()", store)
        self.assertIn("if (nCell <= 0) return;", store)
        apply = self.bodies["OpexC70ApplyCells"]
        self.assertIn("OpexC70Median(distances)", apply)
        self.assertIn("if (sample.distance < median)", apply)
        self.assertIn('OpexC70StoreCell(mode, cellKind, "short"', apply)
        self.assertIn('OpexC70StoreCell(mode, cellKind, "long"', apply)
        self.assertEqual(self.models.count("function OpexC70Median("), 1)
        self.assertEqual(self.models.count("function OpexC70ApplyCells("), 1)
        self.assertIn("OpexC70ApplyCells(lines, year)", self.report)
        self.assertIn("OpexC70ApplyCells(lines, null)", self.models)

    def test_cargo_distance_fields_and_fallbacks(self):
        kind = self.bodies["OpexC70CargoKind"]
        self.assertIn("AICargo.CC_PASSENGERS", kind)
        self.assertIn("AICargo.CC_MAIL", kind)
        self.assertIn('return "pax";', kind)
        self.assertIn('return "freight";', kind)
        self.assertIn("AICargo.IsValidCargo(cargo)", kind)
        collect = self.bodies["OpexC70CollectCellSamples"]
        self.assertIn('if (!("cargo" in line) || !("distance" in line)) continue;', collect)
        self.assertIn("line.cargo", collect)
        self.assertIn("line.distance", collect)
        self.assertIn("line.c70Real.tofloat() / line.c70Pred.tofloat()", collect)
        cell = self.bodies["OpexC70CellFactor"]
        fleet = cell.split("if (fleet)", 1)[1].split("} else {", 1)[0]
        other = cell.split("} else {", 1)[1]
        self.assertIn("project.payload.line", fleet)
        self.assertIn("line.distance", fleet)
        self.assertNotIn("project.distance", fleet)
        self.assertIn('if (!("distance" in line)) return null;', fleet)
        self.assertIn("project.distance", other)
        self.assertIn('if (mode == "fleet")', self.bodies["OpexC70FactorCells"])
        self.assertIn('mode = "air";', self.bodies["OpexC70FactorCells"])
        self.assertIn("if (cellK != null) return cellK;", self.bodies["OpexC70FactorCells"])
        for name in ("task_rail.nut", "task_road.nut", "task_air.nut", "task_water.nut"):
            created = self.sources[name].split("this._lines.append({", 1)[1].split("});", 1)[0]
            self.assertIn("cargo =", created, name)
            self.assertIn("distance =", created, name)

    def test_journal_next_to_mode_factor(self):
        store = self.bodies["OpexC70StoreCell"]
        self.assertLess(store.index("if (year != null && C69_BOTTLENECK_PROBE)"),
                        store.index("OpexC69Log("))
        log = store[store.index("OpexC69Log("):]
        for token in ("phase=c70_factor", "mode=", "kind=", "band=", "median=", "n=", "k="):
            self.assertIn(token, log)
        self.assertIn('OpexC70PublishModeFactors(c70Sums, year, this._lines);', self.report)

    def test_no_arbitrary_distance_threshold_or_squirrel_traps(self):
        for name, body in self.bodies.items():
            code = squirrel_code(body)
            numbers = [int(token) for token in re.findall(r"\b\d+\b", code)]
            self.assertTrue(all(n < 3 for n in numbers), (name, numbers))
            self.assertNotIn("function", code.split("{", 1)[1])
            for word in RESERVED:
                self.assertIsNone(
                    re.search(r"\b" + word + r"\b", code),
                    (name, word))
