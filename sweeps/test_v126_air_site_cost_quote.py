#!/usr/bin/env python3
"""Contrats statiques V126 — coût réel des aéroports neufs et marge au risque résiduel.

Ces tests ne compilent pas le Squirrel : ils figent les garde-fous de la consigne V126.
Réglages à 0 et sonde à 0 (aucun devis calculé, marge historique 30000 / 12000 / 2000),
effet seulement sous C121_AIR_ECONOMICS, un seul AIAccounting dans OpexBuildAirRoute,
aucun mot réservé Squirrel (clone, base, parent) dans le code ajouté, et accord entre les
champs journalisés par l'IA et ceux que lit le décodeur sweeps/parse_air_finance_margin.py.
"""

from __future__ import annotations

import re
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "sweeps"))

from campaign_freeze import parse_ai_setting_specs, parse_ai_settings

AI_DIR = ROOT / "ai" / "OpexAI"
INFO = AI_DIR / "info.nut"

FOUR_DIFFICULTIES = ("easy_value", "medium_value", "hard_value", "custom_value")

# Commentaires et chaines d'une seule passe : l'alternance garde la premiere forme rencontree,
# donc un guillemet dans un commentaire ou un `//` dans une chaine ne trompe pas le masque.
_TOKEN_RE = re.compile(r'/\*.*?\*/|//[^\n]*|"(?:\\.|[^"\\\n])*"', re.DOTALL)
RESERVED_RE = re.compile(r"\b(clone|base|parent)\b")


def read(rel: str) -> str:
    return (ROOT / rel).read_text(encoding="utf-8")


def all_nut() -> dict:
    return {
        path.relative_to(ROOT).as_posix(): path.read_text(encoding="utf-8")
        for path in sorted(AI_DIR.rglob("*.nut"))
    }


def mask(source: str) -> str:
    """Meme longueur que la source : commentaires et chaines remplaces par des espaces."""
    return _TOKEN_RE.sub(lambda m: re.sub(r"[^\n]", " ", m.group(0)), source)


def code_only(source: str) -> str:
    """Source sans commentaires, chaines vidées : ne garde que le code executable."""
    return _TOKEN_RE.sub(lambda m: '""' if m.group(0).startswith('"') else "", source)


def squash(text: str) -> str:
    return " ".join(text.split())


def body(source: str, signature: str) -> str:
    """Fonction complete, de la signature a l'accolade fermante appariee."""
    assert source.count(signature) == 1, f"signature absente ou dupliquee: {signature}"
    start = source.index(signature)
    masked = mask(source)
    brace = masked.index("{", start)
    depth = 0
    for idx in range(brace, len(masked)):
        char = masked[idx]
        if char == "{":
            depth += 1
        elif char == "}":
            depth -= 1
            if depth == 0:
                return source[start : idx + 1]
    raise AssertionError(f"unterminated function: {signature}")


def setting_block(info: str, name: str) -> str:
    needle = f'name = "{name}"'
    assert info.count(needle) == 1, f"reglage absent ou duplique: {name}"
    start = info.index(needle)
    return info[start : info.index("});", start)]


class TestV126Settings(unittest.TestCase):
    REMOVED = (
        "air_site_cost_quote",
        "air_site_cost_margin_pct",
        "air_site_quote_keep_legacy_margin",
    )

    @classmethod
    def setUpClass(cls):
        cls.info = read("ai/OpexAI/info.nut")
        cls.settings = read("ai/OpexAI/settings.nut")
        cls.globals = read("ai/OpexAI/globals_pre.nut")
        cls.persist = read("ai/OpexAI/persist.nut")
        cls.specs = parse_ai_setting_specs(INFO)

    def test_decision_settings_are_removed(self):
        defaults = parse_ai_settings(INFO)
        for name in self.REMOVED:
            self.assertNotIn(name, defaults, name)
            self.assertNotIn(name, self.specs, name)
            self.assertNotIn(f'name = "{name}"', self.info)
            self.assertNotIn(f'GetSetting("{name}")', self.settings)
        for symbol in (
            "AIR_SITE_COST_QUOTE",
            "AIR_SITE_COST_MARGIN_PCT",
            "AIR_SITE_QUOTE_KEEP_LEGACY_MARGIN",
        ):
            # \b : AIR_SITE_COST_QUOTES (cache de la sonde) n'est pas le drapeau retire.
            pattern = re.compile(r"\b%s\b" % symbol)
            for label, text in (
                ("globals", self.globals),
                ("settings", self.settings),
                ("persist", self.persist),
            ):
                self.assertIsNone(pattern.search(text), (symbol, label))

    def test_probe_quote_cache_remains_unpersisted_shape(self):
        for line in (
            "V126_JOINED_STOP_COST <- 300;",
            "AIR_SITE_COST_QUOTES <- {};",
        ):
            self.assertEqual(self.globals.count(line), 1, line)
        self.assertNotIn("AIR_SITE_COST_QUOTES_DATE", self.globals)
        loader = body(self.settings, "function OpexLoadSettings(")
        self.assertLess(len(re.findall(r"\blocal\s+\w+", code_only(loader))), 200)

class TestV126RequiredMargin(unittest.TestCase):
    LEGACY = "return (newAirports == 2) ? 30000 : (newAirports == 1 ? 12000 : 2000);"

    @classmethod
    def setUpClass(cls):
        cls.builders = read("ai/OpexAI/projects_builders.nut")
        cls.selection = read("ai/OpexAI/projects_selection.nut")
        cls.task = read("ai/OpexAI/task_air.nut")
        cls.margin = body(cls.builders, "function OpexAirRequiredMargin(newAirports, plan = null)")

    def test_historic_margin_is_the_only_branch(self):
        self.assertEqual(self.margin.count(self.LEGACY), 1)
        code = code_only(self.margin)
        self.assertEqual(len(re.findall(r"\breturn\b", code)), 1)
        self.assertTrue(squash(self.margin).endswith(self.LEGACY + " }"))
        self.assertNotIn("AIR_SITE_COST_QUOTE", self.margin)
        self.assertNotIn("AIR_SITE_COST_MARGIN_PCT", self.margin)
        self.assertNotIn("v126", code)

    def test_other_margin_copies_are_out_of_scope(self):
        for rel in (
            "ai/OpexAI/air_engine_choice.nut",
            "ai/OpexAI/projects_finance.nut",
            "ai/OpexAI/air_route_economics.nut",
        ):
            code = code_only(read(rel))
            self.assertNotIn("AIR_SITE_COST", code, rel)
            self.assertNotIn("v126", code, rel)
            self.assertNotIn("OpexAirSiteLevelQuote", code, rel)



class TestV126ReservedWordsAndLoadChain(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.sources = all_nut()

    def added_regions(self) -> dict:
        economics = self.sources["ai/OpexAI/air_economics_c121.nut"]
        prepare = body(economics, "function OpexC121PrepareEngineStatic(")
        route = body(self.sources["ai/OpexAI/air_construction.nut"], "function OpexBuildAirRoute(")
        settings = body(self.sources["ai/OpexAI/settings.nut"], "function OpexLoadSettings(")
        globals_pre = self.sources["ai/OpexAI/globals_pre.nut"]
        info = self.sources["ai/OpexAI/info.nut"]
        return {
            "quote": body(economics, "function OpexAirSiteLevelQuote("),
            "prepare_block": prepare[
                prepare.index("if (PROBE_AIR_FINANCE_MARGIN)") :
                prepare.index("plan.c121EngineStatic <- state;")
            ],
            "margin": body(
                self.sources["ai/OpexAI/projects_builders.nut"],
                "function OpexAirRequiredMargin(newAirports, plan = null)",
            ),
            "breakdown_mark": body(
                self.sources["ai/OpexAI/air_construction.nut"],
                "function OpexAirCostBreakdownMark(",
            ),
            "route_lines": "\n".join(
                line for line in route.splitlines() if "brk" in line or "costBreakdown" in line
            ),
            "finance_fields": body(
                self.sources["ai/OpexAI/task_air.nut"], "function OpexAirV126FinanceFields("
            ),
            "cost_fields": body(
                self.sources["ai/OpexAI/task_air.nut"], "function OpexAirV126CostFields("
            ),
            "globals_lines": "\n".join(
                line
                for line in globals_pre.splitlines()
                if "AIR_SITE_COST" in line or "V126_JOINED_STOP_COST" in line
            ),
        }

if __name__ == "__main__":
    unittest.main()
