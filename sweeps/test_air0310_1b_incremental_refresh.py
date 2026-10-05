#!/usr/bin/env python3
"""Contrat statique AIR 03/10 1b : rafraichir en place les projets air publies.

air0310_incremental_refresh vaut 0 aux quatre difficultes. A 1, et seulement
si C121_CATALOG_INCREMENTAL est actif, une publication partielle recrit
planningOpcodes, economicsDate et cargo sur l'objet projet existant au lieu
d'appeler OpexProjectFromAir. C118, C111+decisionEconomics, RestoreWinner N=1
et un changement de cle de groupe gardent la reconversion. Aucune partie
n'est lancee.
"""
from __future__ import annotations

import re
import unittest
from pathlib import Path

from sweeps.campaign_freeze import parse_ai_setting_specs

ROOT = Path(__file__).resolve().parents[1]

SETTING = "air0310_incremental_refresh"
GLOBAL = "AIR0310_INCREMENTAL_REFRESH"
PUBLISH_GLOBAL = "AIR0310_INCREMENTAL_PUBLISH"

# OpexProjectFromAir, lus ligne a ligne. "state" = depend de l'etat courant
# (date, catalog.paxCargo, airOps/N). "plan" = depend du plan inchange.
# "nontrivial" = depend d'un calcul hors formule locale : reconversion.
FROM_AIR_FIELDS = {
    "mode": "plan",
    "kind": "plan",
    "cargo": "state",
    "src": "plan",
    "dst": "plan",
    "payload": "plan",
    "distance": "plan",
    "capital": "plan",
    "budgetCapital": "plan",
    "decisionFinanceCapital": "plan",
    "profitAnnual": "plan",
    "revenueAnnual": "plan",
    "roi": "plan",
    "expectedOpcodes": "plan",
    "budgetScore": "plan",
    "opcodeScore": "plan",
    "planningOpcodes": "state",
    "economicsDate": "state",
    "portfolioProfitAnnual": "plan",
    "portfolioRevenueAnnual": "plan",
    "portfolioDecisionFinanceCapital": "plan",
    "c118TownIds": "nontrivial",
    "c118C68Profit": "plan",
    "c118C68Roi": "plan",
}

STATE_FIELDS = ("planningOpcodes", "economicsDate", "cargo")
RECONVERT_REASONS = ("c118", "c111_decision", "n1_restore", "group_key")


def _read(rel):
    return (ROOT / rel).read_text(encoding="utf-8")


def _setting_block(info, name):
    start = info.index(f'name = "{name}"')
    return info[start:info.index("});", start)]


def _function_body(source, signature):
    start = source.index(signature)
    nxt = source.find("\nfunction ", start + 1)
    if nxt < 0:
        nxt = len(source)
    return source[start:nxt]


def _brace_body(source, signature):
    start = source.index(signature)
    brace = source.index("{", start)
    depth = 0
    for idx in range(brace, len(source)):
        if source[idx] == "{":
            depth += 1
        elif source[idx] == "}":
            depth -= 1
            if depth == 0:
                return source[start:idx + 1]
    raise AssertionError(f"unterminated function: {signature}")


def _explicit_locals(body):
    return re.findall(r"\blocal\s+([A-Za-z_][A-Za-z0-9_]*)", body)


def _brace_balance(text):
    depth = 0
    i = 0
    n = len(text)
    while i < n:
        ch = text[i]
        if ch == '"':
            i += 1
            while i < n and text[i] != '"':
                if text[i] == "\\":
                    i += 1
                i += 1
        elif ch == "'":
            i += 1
            while i < n and text[i] != "'":
                if text[i] == "\\":
                    i += 1
                i += 1
        elif text.startswith("//", i):
            i = text.find("\n", i)
            if i < 0:
                break
        elif text.startswith("/*", i):
            end = text.find("*/", i + 2)
            i = n if end < 0 else end + 2
            continue
        elif ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth < 0:
                return depth
        i += 1
    return depth


def _pair_key(kind, cargo, src, dst):
    if kind == "pax" and src > dst:
        src, dst = dst, src
    return f"{kind}|{cargo}|{src}|{dst}"


def _needs_reconvert(project, catalog_cargo, payload, slot_key, flags):
    """Meme predicat que OpexAir0310PublishedAirNeedsReconvert."""
    if flags.get("c118"):
        return "c118"
    if flags.get("c111") and payload.get("decisionEconomics") is not None:
        return "c111_decision"
    if flags.get("n1") and payload.get("c121Air0310N1"):
        return "n1_restore"
    site_a = payload.get("siteA") or {}
    site_b = payload.get("siteB") or {}
    town_a = site_a.get("town")
    town_b = site_b.get("town")
    if town_a is None or town_b is None:
        return "group_key"
    expected = _pair_key("pax", catalog_cargo, town_a["tile"], town_b["tile"])
    if expected != slot_key:
        return "group_key"
    current = _pair_key(project["kind"], project["cargo"], project["src"], project["dst"])
    if current != expected:
        return "group_key"
    return None


def _still_valid(payload, c121_air_economics=True):
    economics = payload.get("economics")
    if economics is None:
        return False
    decision = payload.get("decisionEconomics") if c121_air_economics else None
    if decision is None:
        decision = economics
    for table in (economics, decision):
        if table["profitAnnual"] <= 0 or table["revenueAnnual"] <= 0 or table["capital"] <= 0:
            return False
    return True


def _refresh_in_place(project, catalog_cargo, planning_ops, date):
    project["planningOpcodes"] = planning_ops
    project["economicsDate"] = date
    project["cargo"] = catalog_cargo
    return project


class TestAir0310_1bIncrementalRefresh(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.info = _read("ai/OpexAI/info.nut")
        cls.globals = _read("ai/OpexAI/globals_pre.nut")
        cls.settings = _read("ai/OpexAI/settings.nut")
        cls.persist = _read("ai/OpexAI/persist.nut")
        cls.update = _read("ai/OpexAI/projects_update.nut")
        cls.builders = _read("ai/OpexAI/projects_builders.nut")
        cls.scheduler = _read("ai/OpexAI/scheduler_tasks.nut")
        cls.models = _read("ai/OpexAI/projects_models.nut")
        cls.publish = _function_body(
            cls.update, "function OpexAir0310PublishIncremental("
        )
        cls.needs = _brace_body(
            cls.update, "function OpexAir0310PublishedAirNeedsReconvert("
        )
        cls.valid = _brace_body(
            cls.update, "function OpexAir0310PublishedAirStillValid("
        )
        cls.refresh = _brace_body(
            cls.update, "function OpexAir0310RefreshPublishedAir("
        )
        cls.from_air = _brace_body(
            cls.builders, "function OpexProjectFromAir("
        )
        cls.key_for = _function_body(cls.models, "function OpexProjectKeyFor(")
        cls.pair_key = _function_body(cls.models, "function OpexProjectPairKey(")
        note_at = cls.update.index(
            "Champs d'OpexProjectFromAir qui changent d'une publication"
        )
        cls.noted = cls.update[note_at:cls.update.index(
            "function OpexAir0310PublishIncremental("
        )]

    def test_setting_defaults_to_zero_and_is_not_persisted(self):
        self.assertEqual(self.info.count(f'name = "{SETTING}"'), 1)
        block = _setting_block(self.info, SETTING)
        self.assertIn("flags = AICONFIG_BOOLEAN", block)
        self.assertIn("min_value = 0", block)
        self.assertIn("max_value = 1", block)
        self.assertIn("step_size = 1", block)
        for key in ("easy_value", "medium_value", "hard_value", "custom_value"):
            self.assertIn(f"{key} = 0", block)
            self.assertNotIn(f"{key} = 1", block)
        spec = parse_ai_setting_specs(ROOT / "ai/OpexAI/info.nut")[SETTING]
        self.assertTrue(spec["boolean"])
        self.assertEqual(spec["default"], 0)
        self.assertEqual(self.globals.count(f"{GLOBAL} <- false;"), 1)
        self.assertEqual(self.globals.count(f"{GLOBAL} <-"), 1)
        self.assertEqual(
            self.settings.count(f'AIController.GetSetting("{SETTING}")'), 1
        )
        self.assertIn(
            f"{GLOBAL} = C121_CATALOG_INCREMENTAL\n"
            f'      && AIController.GetSetting("{SETTING}") != 0;',
            self.settings,
        )
        self.assertNotIn(f"{GLOBAL} <-", self.settings)
        self.assertNotIn(SETTING, self.persist)
        self.assertNotIn(GLOBAL, self.persist)
        publish_load = (
            f"{PUBLISH_GLOBAL} = C121_CATALOG_INCREMENTAL\n"
            f'      && AIController.GetSetting("air0310_incremental_publish") != 0;'
        )
        refresh_load = (
            f"{GLOBAL} = C121_CATALOG_INCREMENTAL\n"
            f'      && AIController.GetSetting("{SETTING}") != 0;'
        )
        self.assertLess(
            self.settings.index(publish_load), self.settings.index(refresh_load)
        )

    def test_from_air_state_fields_match_in_place_formulas(self):
        self.assertEqual(
            {name for name, kind in FROM_AIR_FIELDS.items() if kind == "state"},
            set(STATE_FIELDS),
        )
        self.assertIn("planningOpcodes = planningOps", self.from_air)
        self.assertIn("economicsDate = AIDate.GetCurrentDate()", self.from_air)
        self.assertIn("cargo = catalog.paxCargo", self.from_air)
        self.assertIn("project.planningOpcodes = planningOps;", self.refresh)
        self.assertIn("project.economicsDate = AIDate.GetCurrentDate();", self.refresh)
        self.assertIn("project.cargo = catalog.paxCargo;", self.refresh)
        self.assertNotIn("OpexProjectFromAir(", self.refresh)
        self.assertNotIn("OpexAir0310WriteProject(", self.refresh)
        self.assertNotIn("OpexAir0310RestoreWinner(", self.refresh)
        self.assertNotIn("budgetScore", self.refresh)
        self.assertNotIn("opcodeScore", self.refresh)
        self.assertNotIn("profitAnnual", self.refresh)
        self.assertNotIn("c118TownIds", self.refresh)
        self.assertNotIn("OpexAvailableCapital()", self.from_air)
        self.assertNotIn("OpexAvailableCapital()", self.refresh)

    def test_plan_only_fields_are_not_rewritten_in_place(self):
        plan_fields = [name for name, kind in FROM_AIR_FIELDS.items() if kind == "plan"]
        self.assertIn("mode", plan_fields)
        self.assertIn("src", plan_fields)
        self.assertIn("capital", plan_fields)
        self.assertIn("budgetScore", plan_fields)
        self.assertIn("opcodeScore", plan_fields)
        for name in (
            "mode", "kind", "src", "dst", "distance", "capital", "budgetCapital",
            "decisionFinanceCapital", "profitAnnual", "revenueAnnual", "roi",
            "expectedOpcodes", "budgetScore", "opcodeScore",
            "portfolioProfitAnnual", "c118C68Profit",
        ):
            self.assertNotRegex(self.refresh, rf"project\.{name}\s*=")
        self.assertIn("planningOpcodes = planningOps", self.noted)
        self.assertIn("economicsDate = AIDate.GetCurrentDate()", self.noted)
        self.assertIn("cargo = catalog.paxCargo", self.noted)
        self.assertIn("c118TownIds", self.noted)
        self.assertIn("La caisse n'est pas lue", self.noted)

    def test_reconvert_when_key_c118_c111_or_n1_restore(self):
        self.assertIn("if (C118_AIR_TERRITORIAL_EXPANSION) return true;", self.needs)
        self.assertIn("C111_AIR_C100_DECISION_SHADOW", self.needs)
        self.assertIn("decisionEconomics", self.needs)
        self.assertIn("AIR0310_N1_FALLBACK", self.needs)
        self.assertIn("c121Air0310N1", self.needs)
        self.assertIn('OpexProjectPairKey("pax", catalog.paxCargo, src, dst)', self.needs)
        self.assertIn("OpexProjectKeyFor(project) != expected", self.needs)
        self.assertIn("expected != slotKey", self.needs)
        self.assertIn("if (AIR0310_N1_FALLBACK) OpexAir0310RestoreWinner(plan);", self.from_air)
        self.assertIn("OpexC111ProjectFromAir(catalog, plan, planningOps)", self.from_air)
        self.assertIn("OpexC118PlanCoverageTowns(plan, catalog.paxCargo)", self.from_air)
        self.assertIn("return prefix + OpexProjectPairKey(project.kind, project.cargo, project.src, project.dst);", self.key_for)

    def test_invalidation_matches_from_air_without_restore(self):
        self.assertIn("economics.profitAnnual <= 0", self.valid)
        self.assertIn("economics.revenueAnnual <= 0", self.valid)
        self.assertIn("economics.capital <= 0", self.valid)
        self.assertIn("decisionEconomics.profitAnnual <= 0", self.valid)
        self.assertIn("C121_AIR_ECONOMICS", self.valid)
        self.assertNotIn("OpexAir0310RestoreWinner", self.valid)
        self.assertNotIn("OpexC111ProjectFromAir", self.valid)
        self.assertIn("if (!OpexAir0310PublishedAirStillValid(payload))", self.publish)
        self.assertIn("invalidated++;", self.publish)
        prior = self.publish.index("if (OpexAir0310PriorDropped(")
        refresh_gate = self.publish.index("if (AIR0310_INCREMENTAL_REFRESH")
        from_air = self.publish.index("local refreshed = OpexProjectFromAir(")
        self.assertLess(prior, refresh_gate)
        self.assertLess(refresh_gate, from_air)
        self.assertIn("OpexAir0310PriorDropped(payload, priorRaw, priorKept)", self.publish)

    def test_incremental_loop_keeps_object_and_counts_refresh(self):
        self.assertIn(f"if ({GLOBAL}", self.publish)
        self.assertIn("OpexAir0310PublishedAirNeedsReconvert(project, catalog, payload, slotKey)", self.publish)
        self.assertIn("OpexAir0310RefreshPublishedAir(project, catalog, airOpsPerPlan)", self.publish)
        self.assertIn("refreshedCount++;", self.publish)
        self.assertIn("kept.append(project);", self.publish)
        self.assertIn("local refreshed = OpexProjectFromAir(catalog, payload, airOpsPerPlan);", self.publish)
        self.assertIn("reconverted++;", self.publish)
        self.assertIn("refreshed = refreshedCount", self.publish)
        self.assertGreaterEqual(self.publish.count("OpexProjectFromAir("), 2)
        self.assertLess(
            self.publish.index("local publishCapital = OpexAvailableCapital();"),
            self.publish.index(
                "OpexReselectProjects(projects, publishCapital, owner._abandonedPairs, owner._lines,"
            ),
        )
        names = _explicit_locals(self.publish)
        self.assertEqual(len(names), len(set(names)), names)
        self.assertEqual(_brace_balance(self.update), 0)
        self.assertEqual(_brace_balance(self.scheduler), 0)
        self.assertIn("refreshed=", self.scheduler)
        self.assertIn("publishRefreshed", self.scheduler)

    def test_python_refresh_keeps_groups_values_and_identity(self):
        payload = {
            "economics": {"profitAnnual": 100, "revenueAnnual": 200, "capital": 50},
            "siteA": {"town": {"tile": 10}},
            "siteB": {"town": {"tile": 20}},
        }
        project = {
            "mode": "air",
            "kind": "pax",
            "cargo": 0,
            "src": 10,
            "dst": 20,
            "payload": payload,
            "distance": 12,
            "capital": 50,
            "budgetCapital": 62,
            "decisionFinanceCapital": 62,
            "profitAnnual": 100,
            "revenueAnnual": 200,
            "roi": 2,
            "expectedOpcodes": 100000,
            "budgetScore": 3,
            "opcodeScore": 2,
            "planningOpcodes": 900,
            "economicsDate": 1,
        }
        slot = _pair_key("pax", 0, 10, 20)
        self.assertIsNone(_needs_reconvert(project, 0, payload, slot, {}))
        self.assertTrue(_still_valid(payload))
        same = _refresh_in_place(project, 0, 400, 99)
        self.assertIs(same, project)
        self.assertEqual(project["planningOpcodes"], 400)
        self.assertEqual(project["economicsDate"], 99)
        self.assertEqual(project["cargo"], 0)
        self.assertEqual(project["profitAnnual"], 100)
        self.assertEqual(project["budgetScore"], 3)
        self.assertEqual(project["opcodeScore"], 2)
        self.assertEqual(project["capital"], 50)
        self.assertEqual(_pair_key(project["kind"], project["cargo"], project["src"], project["dst"]), slot)

        payload["economics"] = {"profitAnnual": 0, "revenueAnnual": 200, "capital": 50}
        self.assertFalse(_still_valid(payload))
        payload["economics"] = {"profitAnnual": 100, "revenueAnnual": 200, "capital": 50}

        self.assertEqual(
            _needs_reconvert(project, 0, payload, slot, {"c118": True}), "c118"
        )
        payload["decisionEconomics"] = {"profitAnnual": 80, "revenueAnnual": 180, "capital": 40}
        self.assertEqual(
            _needs_reconvert(project, 0, payload, slot, {"c111": True}),
            "c111_decision",
        )
        payload["c121Air0310N1"] = True
        self.assertEqual(
            _needs_reconvert(project, 0, payload, slot, {"n1": True}), "n1_restore"
        )
        payload["c121Air0310N1"] = False
        payload["decisionEconomics"] = None
        self.assertEqual(
            _needs_reconvert(project, 1, payload, slot, {}), "group_key"
        )
        self.assertEqual(
            set(RECONVERT_REASONS),
            {"c118", "c111_decision", "n1_restore", "group_key"},
        )


if __name__ == "__main__":
    unittest.main()
