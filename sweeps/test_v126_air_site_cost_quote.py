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

    def test_quote_cache_is_not_persisted(self):
        self.assertNotIn("AIR_SITE_COST_QUOTE", self.persist)
        self.assertNotIn("AIR_SITE_COST_QUOTES", self.persist)
        owners = sorted(
            rel for rel, text in all_nut().items() if "AIR_SITE_COST_QUOTES" in code_only(text)
        )
        self.assertEqual(
            owners, ["ai/OpexAI/air_economics_c121.nut", "ai/OpexAI/globals_pre.nut"]
        )

class TestV126QuoteFunction(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.economics = read("ai/OpexAI/air_economics_c121.nut")
        cls.planning = read("ai/OpexAI/air_planning.nut")
        cls.quote = body(cls.economics, "function OpexAirSiteLevelQuote(")

    def test_memoised_per_anchor_and_airport_type(self):
        self.assertIn('local key = site.anchor + "|" + airport.type;', self.quote)
        self.assertNotIn("siteB", self.quote)  # un site, pas une paire
        self.assertIn("local today = AIDate.GetCurrentDate();", self.quote)
        self.assertIn("if (key in AIR_SITE_COST_QUOTES) {", self.quote)
        self.assertIn("if (today - entry.date < 365) return entry.level;", self.quote)
        self.assertIn("AIR_SITE_COST_QUOTES[key] <- { level = level, date = today };", self.quote)
        self.assertTrue(squash(self.quote).endswith("return level; }"))

    def test_reuses_the_v95_levelling_quote_without_duplicating_it(self):
        self.assertEqual(self.planning.count("function OpexAirV95LevelCost("), 1)
        self.assertEqual(self.quote.count("OpexAirV95LevelCost(site, airport)"), 1)
        code = code_only(self.quote)
        for forbidden in ("AIAccounting", "AITestMode", "LevelTiles"):
            self.assertNotIn(forbidden, code)

    def test_defined_once_and_called_only_from_prepare_engine_static(self):
        definitions = 0
        callers = []
        for rel, text in all_nut().items():
            code = code_only(text)
            definitions += code.count("function OpexAirSiteLevelQuote(")
            for match in re.finditer(r"\bOpexAirSiteLevelQuote\(", code):
                if not code[: match.start()].rstrip().endswith("function"):
                    callers.append(rel)
        self.assertEqual(definitions, 1)
        self.assertEqual(callers, ["ai/OpexAI/air_economics_c121.nut"] * 2)


class TestV126PrepareEngineStatic(unittest.TestCase):
    GUARD = "if (PROBE_AIR_FINANCE_MARGIN) {"
    END = "plan.c121EngineStatic <- state;"

    @classmethod
    def setUpClass(cls):
        cls.economics = read("ai/OpexAI/air_economics_c121.nut")
        cls.prepare = body(cls.economics, "function OpexC121PrepareEngineStatic(")
        cls.guard_at = cls.prepare.index(cls.GUARD)
        cls.end_at = cls.prepare.index(cls.END)
        cls.before = cls.prepare[: cls.guard_at]
        cls.block = cls.prepare[cls.guard_at : cls.end_at]
        cls.after = cls.prepare[cls.end_at :]

    def test_quote_computation_is_guarded_by_the_probe_only(self):
        self.assertEqual(self.prepare.count(self.GUARD), 1)
        self.assertNotIn("AIR_SITE_COST_QUOTE", self.prepare)
        self.assertLess(self.prepare.index("local state = {"), self.guard_at)
        self.assertLess(self.guard_at, self.end_at)
        for part in (self.before, self.after):
            code = code_only(part)
            self.assertNotIn("OpexAirSiteLevelQuote", code)
            self.assertNotIn("AIR_SITE_COST_QUOTE", code)
            self.assertNotIn("V126_JOINED_STOP_COST", code)
            self.assertNotIn("v126", code)
        self.assertEqual(self.block.count("OpexAirSiteLevelQuote("), 2)

    def test_only_new_endpoints_are_quoted(self):
        self.assertIn(
            "local levelA = reuseA ? 0 : OpexAirSiteLevelQuote(plan.siteA, plan.airport);",
            self.block,
        )
        self.assertIn(
            "local levelB = reuseB ? 0 : OpexAirSiteLevelQuote(plan.siteB, plan.airport);",
            self.block,
        )
        self.assertIn("state.v126LevelA <- reuseA ? -2 : levelA;", self.block)
        self.assertIn("state.v126LevelB <- reuseB ? -2 : levelB;", self.block)

    def test_quote_arithmetic(self):
        flat = squash(self.block)
        self.assertIn("local levelKnown = (levelA > 0 ? levelA : 0) + (levelB > 0 ? levelB : 0);", flat)
        self.assertIn("local quoteFail = (levelA < 0 ? 1 : 0) + (levelB < 0 ? 1 : 0);", flat)
        self.assertIn(
            "local stopsModel = AIR_JOINED_STOPS ? newAirportCount * AIR_JOINED_STOP_LIMIT "
            "* V126_JOINED_STOP_COST : 0;",
            flat,
        )
        self.assertIn("local siteCost = newAirportCount * plan.airport.price + levelKnown;", flat)
        self.assertIn("local extra = 0;", flat)
        self.assertNotIn("AIR_SITE_COST_QUOTE", flat)

    def test_capital_stays_the_catalogue_price(self):
        self.assertNotIn("state.airportCapital", self.block)
        self.assertEqual(
            self.before.count("airportCapital = newAirportCount * plan.airport.price,"), 1
        )
        assignments = re.findall(r"state\.airportCapital\s*=[^=]", code_only(self.prepare))
        self.assertEqual(assignments, [])

    def test_amortisation_and_maintenance_are_untouched(self):
        flat_before = squash(self.before)
        self.assertIn(
            "airportAmortAnnual = (newAirportCount * plan.airport.price * INFRA_AMORT_PCT / 100) / 30,",
            flat_before,
        )
        self.assertIn(
            "airportMaintenanceAnnual = infrastructureMaintenance "
            "? 12 * newAirportCount * plan.airport.maintenance : 0,",
            flat_before,
        )
        self.assertNotIn("airportAmortAnnual", self.block)
        self.assertNotIn("airportMaintenanceAnnual", self.block)

    def test_new_state_fields_use_the_new_slot_operator(self):
        found = re.findall(r"state\.(v126\w+)\s*(<-|=)(?!=)", self.block)
        self.assertEqual(
            sorted(name for name, _ in found),
            sorted(
                [
                    "v126Extra",
                    "v126LevelA",
                    "v126LevelB",
                    "v126Quoted",
                    "v126QuoteFail",
                    "v126SiteCost",
                    "v126StopsModel",
                ]
            ),
        )
        for name, operator in found:
            self.assertEqual(operator, "<-", name)
        self.assertIn("state.v126Quoted <- true;", self.block)

    def test_v126_is_confined_to_the_two_new_functions(self):
        quote = body(self.economics, "function OpexAirSiteLevelQuote(")
        rest = code_only(self.economics.replace(self.prepare, "").replace(quote, ""))
        self.assertNotRegex(rest, r"v126|V126|\bAIR_SITE_COST_QUOTE\b|AIR_SITE_COST_MARGIN_PCT")
        # Les deux replis sans etat C121 (economie et invariants un-ou-deux avions) lisent
        # toujours le prix catalogue seul : ils restent inchanges.
        self.assertEqual(
            squash(rest).count(
                "local airportCapital = engineStatic != null ? engineStatic.airportCapital "
                ": newAirportCount * plan.airport.price;"
            ),
            2,
        )


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

    def test_active_callers_pass_their_plan(self):
        for signature in (
            "function OpexProjectFromAir(",
        ):
            part = body(self.builders, signature)
            self.assertEqual(part.count("OpexAirRequiredMargin(newAirports, plan)"), 1, signature)
        legacy = body(self.task, "function OpexAI::_tryBuildAir(")
        self.assertEqual(legacy.count("OpexAirRequiredMargin(newAirports, plan)"), 1)
        portfolio = body(self.task, "function OpexAI::_tryBuildAirProject(")
        self.assertEqual(portfolio.count("OpexAirRequiredMargin(newAirports, buildPlan)"), 1)
        probe = body(self.selection, "function OpexAirFinanceMarginLogSelect(")
        self.assertIn('local plan = ("payload" in project) ? project.payload : null;', probe)
        self.assertEqual(probe.count("OpexAirRequiredMargin(newAirports, plan)"), 1)

    def test_every_other_call_is_the_legacy_margin_of_the_probe_helper(self):
        calls = []
        for rel, text in all_nut().items():
            for match in re.finditer(r"\bOpexAirRequiredMargin\(([^()]*)\)", code_only(text)):
                if "newAirports, plan = null" in match.group(1):
                    continue  # la definition
                calls.append((rel, match.group(1).strip()))
        one_argument = [call for call in calls if "," not in call[1]]
        self.assertEqual(one_argument, [("ai/OpexAI/task_air.nut", "st.newAirportCount")])
        self.assertEqual(len(calls), 5)

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


class TestV126ProbeData(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.construction = read("ai/OpexAI/air_construction.nut")
        cls.task = read("ai/OpexAI/task_air.nut")
        cls.route = body(cls.construction, "function OpexBuildAirRoute(")
        cls.mark = body(cls.construction, "function OpexAirCostBreakdownMark(")
        cls.finance = body(cls.task, "function OpexAirV126FinanceFields(")
        cls.cost = body(cls.task, "function OpexAirV126CostFields(")

    def test_build_route_keeps_a_single_accounting(self):
        code = code_only(self.route)
        self.assertEqual(code.count("AIAccounting()"), 1)
        self.assertIn("local costs = AIAccounting();", self.route)
        # Trois contextes distincts : sonde aéroport, arrêt joint protégé et
        # dépenses de la construction. La route n'en crée toujours qu'un.
        self.assertEqual(code_only(self.construction).count("AIAccounting()"), 3)
        for helper in (self.mark, self.finance, self.cost):
            self.assertNotIn("AIAccounting", code_only(helper))

    def test_breakdown_is_probe_only_and_created_after_the_counter(self):
        flat = squash(self.route)
        self.assertIn(
            "local brk = null; if (PROBE_AIR_FINANCE_MARGIN) { "
            "brk = { levelA = 0, airportA = 0, levelB = 0, airportB = 0, planes = 0, stops = 0 }; "
            "result.costBreakdown <- brk; }",
            flat,
        )
        self.assertLess(
            self.route.index("local costs = AIAccounting();"), self.route.index("local brk = null;")
        )
        self.assertEqual(code_only(self.route).count("costBreakdown"), 1)
        self.assertIn("costs.GetCosts()", self.mark)
        self.assertIn("brk[key] = spent - booked;", self.mark)

    def test_every_mark_is_guarded_and_ordered(self):
        lines = [line for line in self.route.splitlines() if "OpexAirCostBreakdownMark(" in line]
        self.assertTrue(lines)
        for line in lines:
            self.assertIn("if (brk != null) OpexAirCostBreakdownMark(costs, brk, ", line)
        keys = [re.search(r'brk, "(\w+)"\)', line).group(1) for line in lines]
        for key in ("levelA", "airportA", "levelB", "airportB"):
            self.assertEqual(keys.count(key), 1, key)
        self.assertGreaterEqual(keys.count("planes"), 9)  # sorties d'echec + fin des avions
        self.assertEqual(set(keys), {"levelA", "airportA", "levelB", "airportB", "planes"})
        order = [keys.index(key) for key in ("levelA", "airportA", "levelB", "airportB")]
        self.assertEqual(order, sorted(order))
        self.assertIn("if (brk != null) brk.stops = result.joinedStopCost;", self.route)

    def test_partial_breakdown_on_every_failure_reason_after_the_counter(self):
        for reason in ("BFAIL", "STNFAIL", "HANGAR", "PLANE", "ORDFAIL", "START"):
            seen = False
            for match in re.finditer(r'result\.reason = [^;]*"%s"[^;]*;' % reason, self.route):
                seen = True
                window = self.route[max(0, match.start() - 200) : match.start()]
                self.assertIn('OpexAirCostBreakdownMark(costs, brk, "planes");', window, reason)
            self.assertTrue(seen, reason)
        # AFAIL : cout de l'aeroport A deja ventile par la marque `airportA`.
        self.assertIn('OpexAirCostBreakdownMark(costs, brk, "airportA");', self.route)

    def test_finance_try_lines_carry_the_v126_fields(self):
        legacy = body(self.task, "function OpexAI::_tryBuildAir(")
        portfolio = body(self.task, "function OpexAI::_tryBuildAirProject(")
        for part, plan_name in ((legacy, "plan"), (portfolio, "buildPlan")):
            self.assertEqual(part.count(f"OpexAirV126FinanceFields({plan_name})"), 2)
            self.assertEqual(part.count("OpexAirV126CostFields(result)"), 1)
            # Les champs existants gardent leur ordre : les champs V126 viennent apres `line=`.
            line_at = part.index('" line=" + this._nextLineId')
            self.assertLess(line_at, part.index("OpexAirV126CostFields(result)"))
            self.assertLess(
                line_at, part.index(f"OpexAirV126FinanceFields({plan_name}) + OpexAirV126Cost")
            )
            for literal in (
                '" planned=" + result.plannedCapital',
                '" actual=" + result.actualCost',
                '" reason=" + result.reason',
            ):
                self.assertIn(literal.strip(), part)
        self.assertEqual(self.task.count('"AIR_FINANCE_TRY'), 1)

    def test_emitter_and_decoder_agree_on_the_field_names(self):
        from parse_air_finance_margin import V126_OPTIONAL_FIELDS, V126_REQUIRED_FIELDS

        emitted = self.finance + self.cost
        for field in V126_REQUIRED_FIELDS + V126_OPTIONAL_FIELDS:
            self.assertRegex(emitted, r'" %s="|"[^"]*\b%s=' % (field, field), field)
        self.assertIn('" v126=" + flag + " quoted=0"', self.finance)
        self.assertIn("local legacyMargin = OpexAirRequiredMargin(st.newAirportCount);", self.finance)
        self.assertIn('" margin_legacy=" + legacyMargin', self.finance)
        # La sonde publie le repli historique lorsque le devis a échoué,
        # sinon le plancher 2000 (pourcentage de marge résiduelle figé à 0).
        self.assertIn('" margin_v126=" + (st.v126QuoteFail > 0', self.finance)
        self.assertRegex(
            self.finance,
            r"st\.v126QuoteFail > 0\s*\? legacyMargin\s*:\s*2000\)",
        )
        self.assertNotIn("AIR_SITE_COST_MARGIN_PCT", self.finance)
        self.assertNotIn("AIR_SITE_COST_QUOTE", self.finance)
        self.assertIn('airport_price=" + plan.airport.price', self.finance)

    def test_probe_helpers_read_only(self):
        for helper in (self.finance, self.cost):
            code = code_only(helper)
            self.assertNotIn("PROBE_AIR_FINANCE_MARGIN", code)
            self.assertNotIn("AICompany", code)
            self.assertNotIn("AITile", code)
            self.assertNotIn("<-", code)


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

    def test_no_reserved_squirrel_identifier_in_added_code(self):
        regions = self.added_regions()
        for name, text in regions.items():
            self.assertTrue(text.strip(), name)
            self.assertIsNone(RESERVED_RE.search(code_only(text)), name)

    def test_added_squirrel_has_balanced_braces_and_parentheses(self):
        for name, text in self.added_regions().items():
            if name in ("route_lines", "globals_lines"):
                continue  # extraits de lignes : l'equilibre n'a de sens que par fonction/bloc
            code = code_only(text)
            self.assertEqual(code.count("{"), code.count("}"), name)
            self.assertEqual(code.count("("), code.count(")"), name)
            self.assertEqual(code.count("["), code.count("]"), name)

    def test_new_functions_are_defined_once_in_modules_the_chain_loads(self):
        expected = {
            "OpexAirSiteLevelQuote": "ai/OpexAI/air_economics_c121.nut",
            "OpexAirCostBreakdownMark": "ai/OpexAI/air_construction.nut",
            "OpexAirV126FinanceFields": "ai/OpexAI/task_air.nut",
            "OpexAirV126CostFields": "ai/OpexAI/task_air.nut",
        }
        for name, rel in expected.items():
            owners = [
                path
                for path, text in self.sources.items()
                if re.search(r"^function %s\(" % name, code_only(text), re.MULTILINE)
            ]
            self.assertEqual(owners, [rel], name)
        main = self.sources["ai/OpexAI/main.nut"]
        builder_air = self.sources["ai/OpexAI/builder_air.nut"]
        projects = self.sources["ai/OpexAI/projects.nut"]
        self.assertLess(
            main.index('require("globals_pre.nut");'), main.index('require("builder_air.nut");')
        )
        self.assertLess(
            main.index('require("globals_pre.nut");'), main.index('require("projects.nut");')
        )
        for module in ("air_economics_c121.nut", "air_planning.nut", "air_construction.nut"):
            self.assertIn(f'require("{module}");', builder_air)
        for module in ("projects_builders.nut", "projects_selection.nut"):
            self.assertIn(f'require("{module}");', projects)
        for module in ("settings.nut", "task_air.nut"):
            self.assertIn(f'require("{module}");', main)


if __name__ == "__main__":
    unittest.main()
