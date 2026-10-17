"""AC-08: AIR matériel : compatibilité, ordre et sélection à monde figé.

Fixture pure Python des invariants de _refreshAir, sans interpréteur Squirrel,
API NewGRF, mesure d'opcodes VM ni revendication de neutralité économique.
"""

from dataclasses import dataclass
from pathlib import Path
import random
import unittest

ROOT = Path(__file__).resolve().parents[1]
CATALOG = (ROOT / "ai/OpexAI/catalog.nut").read_text(encoding="utf-8")
ENGINE_CHOICE = (ROOT / "ai/OpexAI/air_engine_choice.nut").read_text(encoding="utf-8")
PLANS = (ROOT / "ai/OpexAI/air_planning.nut").read_text(encoding="utf-8")
SCHED = (ROOT / "ai/OpexAI/scheduler_tasks.nut").read_text(encoding="utf-8")
ORCH = (ROOT / "ai/OpexAI/orchestrator.nut").read_text(encoding="utf-8")


def body(source, signature):
    i = source.index(signature)
    brace = source.index("{", i)
    depth = 0
    for j in range(brace, len(source)):
        if source[j] == "{":
            depth += 1
        elif source[j] == "}":
            depth -= 1
            if depth == 0:
                return source[i:j+1]
    raise AssertionError(signature)


REFRESH_AIR = body(CATALOG, "function OpexCatalog::_refreshAir(")
REFRESH_ALL = body(CATALOG, "function OpexCatalog::refresh(")
REFRESH_MODE = body(ORCH, "function OpexAI::_c77RefreshModeCatalog(")

LARGE = ("INTERNATIONAL", "METROPOLITAN", "LARGE")
SMALL = ("COMMUTER", "SMALL")


@dataclass(frozen=True)
class Engine:
    ident: int
    buildable: bool
    can_refit: bool
    plane_type: str
    capacity: int
    speed: int
    price: int = 100


def model_catalog(engines, valid_types, pax_cargo=0, keep=True, frontier=False):
    """Deux boucles source, sans coûts d'accès aux propriétés NoAI."""
    combos, choices, frontiers = [], {}, {}
    if pax_cargo < 0:
        return combos, choices, frontiers
    listed = [p for p in engines if p.buildable]
    for ap in LARGE + SMALL:
        if ap not in valid_types:
            continue
        large = ap in LARGE
        best = None
        alternatives = []
        for p in listed:
            if not p.can_refit or p.plane_type not in ("BIG", "SMALL"):
                continue
            if not large and p.plane_type != "SMALL":
                continue
            if p.capacity <= 0:
                continue
            prefer = (best is None or
                      (large and p.plane_type == "BIG" and best.plane_type != "BIG") or
                      ((not large or p.plane_type == best.plane_type) and
                       (p.capacity > best.capacity or
                        (p.capacity == best.capacity and p.speed > best.speed))))
            if not prefer and not keep:
                continue
            if keep:
                alternatives.append(p)
            if prefer:
                best = p
        if keep and alternatives:
            choices[ap] = alternatives
            if frontier:
                # Only verifies optional frontier population, not dominance.
                frontiers[ap] = list(alternatives)
        if best is not None:
            combos.append((ap, "large" if large else "small", best.ident))
    return combos, choices, frontiers


def independent_best(engines, ap):
    large = ap in LARGE
    candidates = [p for p in engines if p.buildable and p.can_refit and
                  p.capacity > 0 and p.plane_type in ("BIG", "SMALL") and
                  (large or p.plane_type == "SMALL")]
    if not candidates:
        return None
    # Stabilité : en cas de score identique, conserver le premier de la liste.
    def score(p):
        return (int(large and p.plane_type == "BIG"), p.capacity, p.speed)
    return max(candidates, key=score)


class AC08AirMaterialTests(unittest.TestCase):
    def test_source_buildability_refit_airport_and_catalog_contracts(self):
        for needle in (
            "this.airport = null;", "this.plane = null;", "this.airCombos = [];",
            "this.airPlaneChoicesByAirport = {};",
            "if (this.paxCargo < 0) return;",
            "AIEngineList(AIVehicle.VT_AIR)", "engines.Valuate(AIEngine.IsBuildable);",
            "engines.KeepValue(1);", "AIEngine.CanRefitCargo(e, this.paxCargo)",
            "if (capacity <= 0) continue;", "AIEngine.GetPrice(e)",
            "AIEngine.GetRunningCost(e)", "AIEngine.GetMaximumOrderDistance(e)",
            "AIEngine.GetMaxAge(e) / 365",
        ):
            self.assertIn(needle, REFRESH_AIR)
        for word in ("AT_INTERNATIONAL", "AT_METROPOLITAN", "AT_LARGE",
                     "AT_COMMUTER", "AT_SMALL"):
            self.assertIn(word, REFRESH_AIR)
        self.assertLess(REFRESH_AIR.index("AT_INTERNATIONAL"), REFRESH_AIR.index("AT_LARGE"))
        self.assertLess(REFRESH_AIR.index("// 1. Combo Grand Aeroport"),
                        REFRESH_AIR.index("// 2. Combo Petit Aeroport"))
        self.assertIn("this.airCombos.append({ kind = \"large\"", REFRESH_AIR)
        self.assertIn("this.airCombos.append({ kind = \"small\"", REFRESH_AIR)
        self.assertIn("if (this.airport == null)", REFRESH_AIR)

    def test_small_airports_reject_big_and_large_prefer_big(self):
        self.assertIn("if (planeType != AIAirport.PT_SMALL_PLANE) continue;", REFRESH_AIR)
        self.assertIn("(isBig && !bestIsBig)", REFRESH_AIR)
        self.assertIn("isBig == bestIsBig", REFRESH_AIR)
        engines = [
            Engine(1, True, True, "SMALL", 300, 600),
            Engine(2, True, True, "BIG", 15, 100),
            Engine(3, True, True, "SMALL", 390, 300),
        ]
        combos, choices, _ = model_catalog(engines, set(LARGE+SMALL))
        self.assertEqual([(a, p) for a, _, p in combos if a in LARGE],
                         [(a, 2) for a in LARGE])
        self.assertEqual([(a, p) for a, _, p in combos if a in SMALL],
                         [(a, 3) for a in SMALL])
        self.assertTrue(all(p.plane_type == "SMALL" for key in SMALL for p in choices[key]))

    def test_first_valid_airport_and_order_do_not_get_resorted(self):
        engines = [Engine(1, True, True, "SMALL", 200, 200)]
        valid_types = {"LARGE", "SMALL", "COMMUTER"}
        combos, choices, _ = model_catalog(engines, valid_types)
        self.assertEqual([ap for ap, _, _ in combos], ["LARGE", "COMMUTER", "SMALL"])
        self.assertEqual(combos[0][2], 1)
        self.assertEqual(list(choices), ["LARGE", "COMMUTER", "SMALL"])

    def test_4800_frozen_catalogues_best_choice_and_list_order(self):
        rng = random.Random(20261008)
        for case in range(4800):
            engines = [
                Engine(i, rng.random() > .18, rng.random() > .25,
                       rng.choice(("SMALL", "BIG", "HELICOPTER")),
                       rng.randint(-2, 500), rng.randint(0, 800))
                for i in range(rng.randint(0, 26))
            ]
            valid = {typ for typ in LARGE+SMALL if rng.random() > .22}
            pax = rng.choice((-1, 0, 2, 3))
            for keep in (False, True):
                combos, choices, _ = model_catalog(engines, valid, pax, keep)
                expected = []
                for ap in LARGE + SMALL:
                    chosen = independent_best(engines, ap) if ap in valid and pax >= 0 else None
                    if chosen is not None:
                        expected.append((ap, "large" if ap in LARGE else "small", chosen.ident))
                self.assertEqual(combos, expected, (case, keep))
                if keep:
                    for ap in choices:
                        self.assertEqual([p.ident for p in choices[ap]],
                                         [p.ident for p in engines if p.buildable and p.can_refit
                                          and p.capacity > 0 and p.plane_type in ("SMALL", "BIG")
                                          and (ap in LARGE or p.plane_type == "SMALL")])
                else:
                    self.assertFalse(choices)

    def test_options_frontier_only_when_enabled_and_consumers_still_present(self):
        self.assertIn("local keepPlaneChoices = true;", REFRESH_AIR)
        self.assertIn("if (keepPlaneChoices && probeChoices.len() > 0)", REFRESH_AIR)
        self.assertNotIn("C85_AIR_EQUIPMENT_FRONTIER", REFRESH_AIR)
        self.assertNotIn("OpexAirEquipmentStaticFrontier", REFRESH_AIR)
        self.assertNotIn("airPlaneFrontierByAirport", REFRESH_AIR)
        self.assertIn("catalog.airPlaneChoicesByAirport", ENGINE_CHOICE)
        self.assertNotIn("airPlaneFrontierByAirport", ENGINE_CHOICE)
        self.assertIn("catalog.airPlaneChoicesByAirport", PLANS)
        self.assertIn("catalog.airCombos", PLANS)
        self.assertIn("this._refreshAir();", REFRESH_ALL)
        self.assertIn("this._catalog._refreshAir();", REFRESH_MODE)
        self.assertIn("this._catalog.refresh(this._budget, year);", SCHED)
        engines = [Engine(9, True, True, "SMALL", 10, 90)]
        _, off, off_f = model_catalog(engines, set(SMALL), keep=False)
        _, on, on_f = model_catalog(engines, set(SMALL), keep=True, frontier=False)
        _, _, yes_f = model_catalog(engines, set(SMALL), keep=True, frontier=True)
        self.assertEqual(off, {})
        self.assertEqual(off_f, on_f)
        self.assertEqual(list(on), list(SMALL))
        self.assertEqual(list(yes_f), list(SMALL))

    def test_legacy_cost_source_exists_but_is_not_current_air_refresh_measure(self):
        import json
        data = json.loads((ROOT / "results/catalogue_churn.json").read_text(encoding="utf-8"))
        self.assertEqual(len(data["per_year"]), 20)
        self.assertTrue(all(row["ops_airports"] > 0 for row in data["per_year"]))
        self.assertTrue(all(row["ops_engines"] > row["ops_airports"]
                            for row in data["per_year"]))
        # Données d'un ancien protocole : ne pas tester de valeur d'opcodes
        # pour le _refreshAir C121 courant à partir de ce relevé historique.


if __name__ == "__main__":
    unittest.main()
