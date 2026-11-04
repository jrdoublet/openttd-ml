"""ROAD1Y alt_load : contrats statiques (ne compilent ni n'executent le Squirrel).

road1y_alt_load = N (0..50, defaut 0) : environ N % des bus d'une ligne PAX
route recoivent la liste d'ordres inverse (chargement complet au bout B,
aucun a A) ; les autres gardent l'ordre historique (plein a A sous
road1y_load_orders). Le sens d'un bus se lit dans les drapeaux de ses ordres
0/1, jamais dans un compteur sauvegarde. Un bus inverse ne partage jamais la
liste d'un bus normal. A 0, chaque site d'achat execute le clone historique ;
hors route seule, force a 0.
"""
import re
import unittest
from pathlib import Path

from test_v261_forum_behaviours import body, source

ROOT = Path(__file__).resolve().parents[1]
AI = ROOT / "ai" / "OpexAI"
HELPERS = (
    "OpexRoad1yAltLoadIsInverted",
    "OpexRoad1yAltLoadOrient",
    "OpexRoad1yAltLoadEligible",
    "OpexRoad1yAltLoadClone",
    "OpexRoad1yAltLoadCensus",
)


def _quota(weight, total):
    """Modele Python du quota Squirrel (division entiere, jamais sous 2 bus)."""
    return (weight * total + 50) // 100 if total >= 2 else 0


def _simulate(weight, buses):
    """Achats un par un depuis un premier bus normal : (normaux, inverses)."""
    normal, inverted = 1, 0
    for _ in range(1, buses):
        total = normal + inverted + 1
        if inverted < _quota(weight, total):
            inverted += 1
        else:
            normal += 1
    return normal, inverted


class AltLoadDeclaration(unittest.TestCase):
    def test_global_info_and_both_loaders(self):
        self.assertIn("ROAD1Y_ALT_LOAD <- 0;", source("globals_pre.nut"))
        self.assertIn("ROAD1Y_ALT_LOAD_CENSUS_YM <- -1;", source("globals_pre.nut"))
        block = source("info.nut").split('name = "road1y_alt_load",')[1].split("});")[0]
        self.assertIn("min_value = 0, max_value = 50", block)
        for difficulty in ("easy", "medium", "hard", "custom"):
            self.assertIn(difficulty + "_value = 0", block)
        for loader in ("OpexLoadSettings", "OpexLoadBusDistrictSettings"):
            code = body("settings.nut", loader)
            get_at = code.index('ROAD1Y_ALT_LOAD = AIController.GetSetting("road1y_alt_load");')
            bound_at = code.index("if (ROAD1Y_ALT_LOAD < 0 || ROAD1Y_ALT_LOAD > 50) ROAD1Y_ALT_LOAD = 0;")
            gate_at = code.index("if (!road1yRoadOnly) ROAD1Y_ALT_LOAD = 0;")
            self.assertLess(code.index("local road1yRoadOnly"), get_at, loader)
            self.assertLess(get_at, bound_at, loader)
            self.assertLess(bound_at, gate_at, loader)
        bus = body("settings.nut", "OpexLoadBusDistrictSettings")
        self.assertLess(bus.index("if (!road1yRoadOnly) ROAD1Y_ALT_LOAD = 0;"),
                        bus.index('require("bus_districts.nut")'))

    def test_global_users(self):
        users = sorted(p.name for p in AI.glob("*.nut")
                       if "ROAD1Y_ALT_LOAD" in p.read_text(encoding="utf-8"))
        self.assertEqual(users, ["builder_road.nut", "bus_districts.nut", "globals_pre.nut",
                                 "scheduler_tasks.nut", "settings.nut"])
        for name in HELPERS:
            self.assertIn("function " + name + "(", source("bus_districts.nut"))
        # Le sens se lit dans les ordres : aucune persistance ni reconciliation.
        for name in ("persist.nut", "main.nut", "bus_districts_overrides.nut"):
            self.assertNotIn("AltLoad", source(name), name)


class AltLoadPurchaseSites(unittest.TestCase):
    def test_opening_clone_is_guarded_and_keeps_historical_branch(self):
        code = source("builder_road.nut")
        self.assertIn("    local extra = (ROAD1Y_ALT_LOAD > 0 && !isFreight && (\"kind\" in candidate)\n"
                      "        && candidate.kind == \"pax\" && ROAD1Y_LOAD_ORDERS)\n"
                      "        ? OpexRoad1yAltLoadClone(depot, first, built, \"open\", -1)\n"
                      "        : AIVehicle.CloneVehicle(depot, first, true);", code)

    def test_refleet_both_paths_guarded(self):
        code = body("builder_road.nut", "OpexRoadRefleet")
        alt_at = code.index("local altLoad = ROAD1Y_ALT_LOAD > 0 && OpexRoad1yAltLoadEligible(line);")
        self.assertLess(code.index("local built = [];"), alt_at)
        self.assertLess(alt_at, code.index("if (template != null) {\n    for"))
        self.assertIn("local altFleet = altLoad ? OpexLineVehicleIds(line, AIStation.GetStationID(line.stationA)) : null;", code)
        self.assertIn("? OpexRoad1yAltLoadClone(line.depot, template, altFleet, \"refleet\", altLineId)\n"
                      "          : AIVehicle.CloneVehicle(line.depot, template, true);", code)
        self.assertIn("if (altLoad) altFleet.append(extra);", code)
        self.assertIn("? OpexRoad1yAltLoadClone(line.depot, first, built, \"refleet_new\", altLineId)\n"
                      "          : AIVehicle.CloneVehicle(line.depot, first, true);", code)
        # Le premier bus d'une ligne vide garde ses ordres historiques explicites.
        self.assertIn("!AIOrder.AppendOrder(first, line.stationA, sourceFlags)", code)

    def test_weak_transfer_guarded(self):
        code = body("bus_districts.nut", "OpexRoad1yWeakStep")
        self.assertIn("local newVeh = (ROAD1Y_ALT_LOAD > 0 && OpexRoad1yAltLoadEligible(bestStrong))", code)
        self.assertIn("\"weak\", bestStrong.lineId)\n"
                      "            : AIVehicle.CloneVehicle(bestStrong.depot, bestTemplate, true);", code)

    def test_every_road_pax_clone_site_is_covered(self):
        calls = 0
        for name in ("builder_road.nut", "bus_districts.nut"):
            calls += len(re.findall(r"OpexRoad1yAltLoadClone\(", source(name)))
        # 1 definition + opening + 2 refleet paths + weak.
        self.assertEqual(calls, 5)
        # Les seuls autres CloneVehicle routiers restants : fourgons postaux (kind mail).
        mail = body("bus_districts.nut", "OpexRoad1yBuildMailChild")
        self.assertIn("AIVehicle.CloneVehicle(parentLine.depot, first, true)", mail)

    def test_census_is_measurement_only(self):
        sched = body("scheduler_tasks.nut", "OpexAI::_dispatchRefleet")
        self.assertIn("if (ROAD1Y_ALT_LOAD > 0 && DECISION_LOG) OpexRoad1yAltLoadCensus(this, year);", sched)
        census = body("bus_districts.nut", "OpexRoad1yAltLoadCensus")
        for forbidden in ("CloneVehicle", "SellVehicle", "SetOrderFlags", "SendVehicleToDepot"):
            self.assertNotIn(forbidden, census)
        self.assertIn('OpexDecide("ROAD1Y_ALT_LOAD_CENSUS"', census)


class AltLoadHelpers(unittest.TestCase):
    def test_orientation_is_read_from_real_order_flags(self):
        code = body("bus_districts.nut", "OpexRoad1yAltLoadIsInverted")
        self.assertIn("AIOrder.GetOrderCount(vehicle) != 2) return false;", code)
        self.assertIn("(AIOrder.GetOrderFlags(vehicle, 0) & fullAny) == 0", code)
        self.assertIn("(AIOrder.GetOrderFlags(vehicle, 1) & fullAny) == fullAny", code)

    def test_orient_only_touches_load_flags_and_verifies(self):
        code = body("bus_districts.nut", "OpexRoad1yAltLoadOrient")
        self.assertIn("AIOrder.GetOrderFlags(vehicle, 0) & ~fullAny", code)
        self.assertIn("AIOrder.GetOrderFlags(vehicle, 1) & ~fullAny", code)
        self.assertIn("return OpexRoad1yAltLoadIsInverted(vehicle) == inverted;", code)

    def test_eligibility(self):
        code = body("bus_districts.nut", "OpexRoad1yAltLoadEligible")
        for fragment in ("ROAD1Y_ALT_LOAD > 0", "ROAD1Y_LOAD_ORDERS", 'line.mode == "road"',
                         'line.kind == "pax"', "road100TourActive"):
            self.assertIn(fragment, code)

    def test_clone_never_shares_across_orientations(self):
        code = body("bus_districts.nut", "OpexRoad1yAltLoadClone")
        self.assertIn("local quota = total >= 2 ? (ROAD1Y_ALT_LOAD * total + 50) / 100 : 0;", code)
        self.assertIn("local wantInverted = twoOrders && inverted < quota;", code)
        self.assertIn("local source = wantInverted ? sameInverted : sameNormal;", code)
        shared = code.index("extra = AIVehicle.CloneVehicle(depot, source, true);")
        copy = code.index("extra = AIVehicle.CloneVehicle(depot, template, false);")
        orient = code.index("OpexRoad1yAltLoadOrient(extra, wantInverted)")
        self.assertLess(shared, copy)
        self.assertLess(copy, orient)
        self.assertIn("AIVehicle.SellVehicle(extra);", code[orient:])
        # Le seul partage hors sens connu est le repli historique (tour a 4 ordres).
        self.assertEqual(code.count(", true);"), 2)
        self.assertIn('how = "historical";\n    extra = AIVehicle.CloneVehicle(depot, template, true);', code)
        log_at = code.index('OpexDecide("ROAD1Y_ALT_LOAD"')
        self.assertIn("if (DECISION_LOG && (wantInverted || how != \"shared\")) {", code[:log_at])

    def test_squirrel_traps_absent_from_new_code(self):
        for name in HELPERS:
            code = body("bus_districts.nut", name)
            self.assertNotIn("function(", code)
            self.assertNotIn(".find(", code)
            for word in ("clone", "base", "parent", "static", "delegate"):
                self.assertIsNone(re.search(r"\b" + word + r"\b", code), (name, word))


class AltLoadModel(unittest.TestCase):
    def test_zero_never_inverts(self):
        for buses in range(1, 16):
            self.assertEqual(_simulate(0, buses), (buses, 0))

    def test_weight_33_targets_one_third(self):
        expected = {1: 0, 2: 1, 3: 1, 4: 1, 5: 2, 6: 2, 7: 2, 8: 3, 12: 4}
        for buses, inverted in expected.items():
            self.assertEqual(_simulate(33, buses)[1], inverted, buses)

    def test_single_bus_never_inverted_and_one_normal_always_kept(self):
        for weight in range(0, 51):
            self.assertEqual(_quota(weight, 1), 0)
            for total in range(2, 30):
                self.assertLess(_quota(weight, total), total)
                normal, inverted = _simulate(weight, total)
                self.assertGreaterEqual(normal, 1)
                self.assertEqual(normal + inverted, total)


if __name__ == "__main__":
    unittest.main()
