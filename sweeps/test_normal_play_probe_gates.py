"""Contrats host-only pour les relevés annuels inutiles à ``probes=0``.

Ces tests sont délibérément TDD : un test ``test_gate_*`` échoue tant que sa
garde Squirrel n'a pas été ajoutée. Aucun banc ni import du runtime IA.

Périmètre : seulement VS/VL, RV et le rapport de panneaux _reportYear.
_reportLines reste indispensable aux décisions (santé, C70/C121, persistance).
RY n'est PAS candidat à une garde DEBUG_SIGNS seule : roadRealSpeed alimente
LINE_REVENUE lorsque DECISION_LOG est activé sans panneaux.
"""

from __future__ import annotations

import re
import unittest
from pathlib import Path


AI = Path(__file__).resolve().parents[1] / "ai" / "OpexAI"


def _source(name: str) -> str:
    return (AI / name).read_text(encoding="utf-8")


def _method(source: str, signature: str) -> str:
    """Isoler un corps Squirrel sans se baser sur des numéros de ligne.

    Le comptage des accolades ignore les commentaires et les chaînes afin que
    les tests restent robustes face à un texte de journal contenant « { ».
    """
    match = re.search(r"\bfunction\s+" + re.escape(signature) + r"\s*\{", source)
    if match is None:
        raise AssertionError(f"méthode introuvable : {signature}")
    start = match.end() - 1
    i = start
    depth = 0
    state = "code"
    quote = ""
    while i < len(source):
        char = source[i]
        next_char = source[i + 1] if i + 1 < len(source) else ""
        if state == "line_comment":
            if char == "\n":
                state = "code"
        elif state == "block_comment":
            if char == "*" and next_char == "/":
                state = "code"
                i += 1
        elif state == "string":
            if char == "\\":
                i += 1
            elif char == quote:
                state = "code"
        elif char == "/" and next_char == "/":
            state = "line_comment"
            i += 1
        elif char == "/" and next_char == "*":
            state = "block_comment"
            i += 1
        elif char in ('"', "'"):
            state = "string"
            quote = char
        elif char == "{":
            depth += 1
        elif char == "}":
            depth -= 1
            if depth == 0:
                return source[start + 1:i]
        i += 1
    raise AssertionError(f"corps non terminé : {signature}")


def _condition_before(body: str, first_statement: str) -> str:
    """Lire le if dont le bloc commence par une instruction diagnostique.

    Évite de confondre une garde ajoutée ailleurs avec celle qui protège les
    appels API coûteux. Les trois conditions concernées n'ont pas de sous-if.
    """
    pattern = r"\bif\s*\((?P<cond>[^()\n]+)\)\s*\{\s*" + re.escape(first_statement)
    match = re.search(pattern, body)
    if match is None:
        raise AssertionError(f"bloc if attendu avant : {first_statement}")
    return match.group("cond")


def _requires_debug_signs(test: unittest.TestCase, condition: str) -> None:
    test.assertRegex(condition, r"\bDEBUG_SIGNS\b", "sonde sans garde DEBUG_SIGNS")
    test.assertNotRegex(condition, r"!\s*DEBUG_SIGNS\b", "garde inversée")
    test.assertIn("&&", condition, "la garde doit préserver le critère métier existant")


class NormalPlayProbeGateContracts(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        source = _source("task_report.nut")
        cls.lines = _method(source, "OpexAI::_reportLines(year)")
        cls.year = _method(source, "OpexAI::_reportYear(year, ranked)")

    def test_baseline_panel_switch_is_mask_bit_two(self) -> None:
        settings = _source("settings.nut")
        info = _source("info.nut")
        self.assertIn('DEBUG_SIGNS = (probes & 2) != 0;', settings)
        spec = info.split('name = "probes"', 1)[1].split("});", 1)[0]
        for level in ("easy", "medium", "hard", "custom"):
            self.assertRegex(spec, rf"\b{level}_value\s*=\s*0\b")

    def test_vs_vl_are_local_and_not_decision_state(self) -> None:
        body = self.lines
        first = "local state = AIVehicle.GetState(v);"
        self.assertIn(first, body)
        begin = body.index(first)
        end = body.index("diagSlot++;", begin) + len("diagSlot++;")
        block = body[begin:end]
        for api in ("AIVehicle.GetState(v)",
                    "AIOrder.ResolveOrderPosition(v, AIOrder.ORDER_CURRENT)",
                    "AIVehicle.GetCurrentSpeed(v)",
                    "AIVehicle.GetCargoLoad(v, line.cargo)"):
            self.assertIn(api, block)
        self.assertIn('OpexSign(anchor, "VS|"', block)
        self.assertIn('OpexSign(anchor, "VL|"', block)
        self.assertNotRegex(block, r"\bline\.\w+\s*(?:<-|=(?!=))")
        self.assertNotRegex(body[end:body.index('OpexSign(anchor, "OZ|"', end)],
                            r"\b(?:state|order|speed|load|diagSlot)\b")

    def test_rv_is_local_and_only_emits_a_panel(self) -> None:
        section = self.lines.split("/* Rendement de vitesse", 1)[1].split("/* Rendement route", 1)[0]
        self.assertIn('OpexSign(anchor, "RV|"', section)
        self.assertIn("AIEngine.GetMaxSpeed(AIVehicle.GetEngineType(v))", section)
        self.assertIn("OpexMedianInt(moving)", section)
        self.assertIn("OpexMedianInt(catalogs)", section)
        self.assertNotRegex(section, r"\bline\.\w+\s*(?:<-|=(?!=))")

    def test_annual_line_health_and_calibration_must_remain_live(self) -> None:
        body = self.lines
        for essential in (
            "this._purgeUnprofitableStreaks();",
            "line.lastLiveVehicles <- vehCount;",
            "line.vehCount <- vehCount;",
            "line.lastProfit <- profit;",
            "line.lastRevenue <- currentRevenue;",
            "OpexC121ObserveLineRealization(",
            "OpexC70C82AccumulateLine(",
            "OpexUpdateFreightLineHealth(",
            "OpexUpdateAirLineHealth(",
        ):
            with self.subTest(essential=essential):
                self.assertIn(essential, body)
        scheduler = _source("scheduler_tasks.nut")
        self.assertIn("this._reportLines(year);", scheduler)

    def test_ry_speed_is_consumed_by_decision_log(self) -> None:
        section = self.lines.split("/* Rendement route", 1)[1].split("local currentRevenue", 1)[0]
        self.assertIn("local roadRealSpeed = -1;", section)
        self.assertIn("roadRealSpeed = OpexMedianInt(moving)", section)
        self.assertIn('real_speed=" + roadRealSpeed', self.lines)
        self.assertIn("if (DECISION_LOG) {", self.lines)
        # Un éventuel ajustement futur doit préserver RY sous DECISION_LOG seul.
        cond = _condition_before(section, "local moving = [];")
        if "DEBUG_SIGNS" in cond:
            self.assertIn("DECISION_LOG", cond)
            self.assertIn("||", cond)

    def test_gate_vs_vl_only_when_debug_signs_enabled(self) -> None:
        """La collecte VS/VL doit être évitée sans panneaux."""
        cond = _condition_before(self.lines, "local state = AIVehicle.GetState(v);")
        self.assertIn("isFreight", cond)
        self.assertIn("diagSlot", cond)
        _requires_debug_signs(self, cond)

    def test_gate_rv_speed_medians_only_when_debug_signs_enabled(self) -> None:
        """La collecte RV doit être évitée sans panneaux."""
        section = self.lines.split("/* Rendement de vitesse", 1)[1].split("/* Rendement route", 1)[0]
        cond = _condition_before(section, "local moving = [];")
        self.assertIn("AIVehicle.VT_RAIL", cond)
        _requires_debug_signs(self, cond)

    def test_gate_yearly_panel_report_but_keep_c78_probe(self) -> None:
        """Le rapport TV/BT se coupe sans panneaux, mais pas la sonde C78."""
        body = self.year
        self.assertIn("this._reportC78Candidates(year);", body)
        self.assertIn("if (C69_BOTTLENECK_PROBE)", body)
        # La sortie anticipée doit se trouver avant OX/TV, et ne pas empêcher C69.
        prefix = body[:body.index('OpexSign(anchor, "OX|"')]
        candidates = re.findall(r"\bif\s*\(([^()\n]*)\)\s*return\s*;", prefix)
        valid = [cond for cond in candidates
                 if "&&" in cond
                 and re.search(r"!\s*DEBUG_SIGNS\b", cond)
                 and re.search(r"!\s*C69_BOTTLENECK_PROBE\b", cond)]
        self.assertTrue(valid,
                        "_reportYear : ajouter une sortie précoce seulement si "
                        "!DEBUG_SIGNS && !C69_BOTTLENECK_PROBE, avant les calculs OX/TV")


if __name__ == "__main__":
    unittest.main()
