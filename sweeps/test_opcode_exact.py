"""Contrats exp_opcode_exact : defauts, bornes, et preuve de Manhattan."""
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def read(rel):
    return (ROOT / rel).read_text(encoding="utf-8")


def body(source, signature):
    start = source.index(signature)
    brace = source.index("{", start)
    depth = 0
    for idx in range(brace, len(source)):
        if source[idx] == "{":
            depth += 1
        elif source[idx] == "}":
            depth -= 1
            if depth == 0:
                return source[start : idx + 1]
    raise AssertionError(f"unterminated function: {signature}")


def setting_block(info, name):
    start = info.index(f'name = "{name}"')
    return info[start:info.index("});", start)]


class OpcodeExactContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.info = read("ai/OpexAI/info.nut")
        cls.settings = read("ai/OpexAI/settings.nut")
        cls.globals = read("ai/OpexAI/globals_pre.nut")
        cls.main = read("ai/OpexAI/main.nut")
        cls.road = read("ai/OpexAI/builder_road.nut")
        cls.exact = read("ai/OpexAI/opcode_exact.nut")
        cls.air = read("ai/OpexAI/task_air.nut")
        cls.coverage = read("ai/OpexAI/air_coverage.nut")
        cls.construction = read("ai/OpexAI/air_construction.nut")
        cls.probes = read("ai/OpexAI/probes.nut")

    def test_settings_defaults(self):
        # exp_opcode_exact adopte le 2026-10-02 (20x10 neutre, regle opcodes) ;
        # le controle double chemin reste un outil de mesure, defaut 0.
        self.assertNotIn('name = "exp_opcode_exact"', read("ai/OpexAI/info.nut"))
        self.assertNotIn('GetSetting("exp_opcode_exact")', read("ai/OpexAI/settings.nut"))
        self.assertNotIn("EXP_OPCODE_EXACT <-", read("ai/OpexAI/globals_pre.nut"))
        self.assertNotIn("EXP_OPCODE_EXACT_ON <-", self.globals)
        self.assertNotIn("exp_opcode_exact_check", self.info)  # V239
        self.assertNotIn("EXP_OPCODE_EXACT_CHECK", self.settings)

    def test_require_and_historical_road_order(self):
        self.assertLess(self.main.index('require("builder_road.nut");'), self.main.index('require("opcode_exact.nut");'))
        for name, target in (("OpexRoadSites", "OpexRoadSitesGated"), ("OpexRoadPaxVoirieSites", "OpexRoadPaxVoirieGated"), ("OpexRoadPlanFor", "OpexRoadPlanForActive")):
            wrapper = body(self.road, "function " + name + "(")
            self.assertIn("return " + target + "(", wrapper)
            self.assertNotIn("EXP_OPCODE_EXACT_ON", wrapper)
            self.assertNotIn("GetCargoProduction", wrapper)
        self.assertIn("function OpexRoadHistoricClassify(", self.exact)

    def test_exact_filters_share_the_historical_ring(self):
        scan = body(self.exact, "function OpexRoadSitesScan(")
        self.assertIn("if (abs(dx) != r && abs(dy) != r) continue;", scan)
        self.assertIn("OpexRoadHistoricClassify", scan)
        self.assertIn("OpexRoadExactClassify", scan)
        self.assertLess(
            scan.index("OpexRoadHistoricClassify"),
            scan.index("OpexRoadExactClassify"),
        )
        historic = body(self.exact, "function OpexRoadHistoricClassify(")
        exact = body(self.exact, "function OpexRoadExactClassify(")
        self.assertLess(historic.index("excludeTiles"), historic.index("GetCargoProduction"))
        self.assertLess(exact.index("GetClosestTown"), exact.index("GetCargoProduction"))
        self.assertLess(exact.index("GetCargoProduction"), exact.index("OpexRoadStopsTooClose"))
        self.assertNotIn("townSet", exact)
        self.assertNotIn("OpexRoadTownSet", self.exact)
        self.assertNotIn("OpexRoadRoadSet", self.exact)
        self.assertIn("return OpexRoadHuntCore(", body(self.exact, "function OpexRoadSitesGated("))
        voirie = body(self.exact, "function OpexRoadVoirieExactClassify(")
        self.assertLess(voirie.index("GetClosestTown"), voirie.index("IsRoadTile"))
        self.assertLess(voirie.index("IsRoadTile"), voirie.index("GetCargoProduction"))
        self.assertLess(voirie.index("GetCargoProduction"), voirie.index("OpexRoadTileTooClose"))

    def test_other_sites_keep_historical_bodies(self):
        fleet = body(self.air, "function OpexAI::_resizeAirFleets(")
        self.assertNotIn("else airLines.sort(OpexAirFleetPriorityCompare);", fleet)
        self.assertIn("airLines = OpexAirFleetSortSelect(airLines);", fleet)
        wrapped = body(self.exact, "function OpexAirFleetSortPrecomputed(")
        self.assertIn("lineYield = OpexAirFleetYield(line)", wrapped)
        self.assertNotIn("line.yield", wrapped)
        catch = body(self.coverage, "function OpexAirStationCatchmentProduction(")
        self.assertIn("return OpexAirStationCatchmentProductionActive(stationId, cargo);", catch)
        self.assertNotIn("AITile.GetCargoProduction", catch)
        summed = body(self.exact, "function OpexAirCatchmentSumExact(")
        self.assertIn("Valuate(AITile.GetCargoProduction, cargo, 1, 1, 0)", summed)
        self.assertNotIn("KeepAboveValue", summed)
        joined = body(self.construction, "function OpexAirBuildJoinedStops(")
        self.assertIn("OpexAirJoinedCandidatesSelect", joined)
        self.assertNotIn("GetCargoProduction", joined)
        self.assertIn("candidates.sort(function(a, b)", joined)
        self.assertNotIn("Historic(", self.exact.replace("OpexRoadHistoricClassify(", "").replace("OpexRoadVoirieHistoricClassify(", ""))  # V238+V239
        step = body(self.probes, "function OpexC117AirThroughputStep(")
        self.assertNotIn("OpexC117AirThroughputStepActive", step)
        self.assertNotIn("EXP_OPCODE_EXACT", step)
        self.assertIn("AIVehicle.GetCapacity(v, line.cargo)", step)
        self.assertIn("AIVehicle.GetRunningCost(v)", step)
        self.assertNotIn("OpexC117ReadCaps", self.probes)
        self.assertNotIn("OpexC117AirThroughputStepActive", self.exact)
        self.assertNotIn("function OpexC117ReadCaps", self.exact)

    def test_manhattan_bound(self):
        """Disque de Chebyshev de rayon R : manhattan max = 2R.
        Un arret a manhattan(centre) >= 2R+D est a distance >= D de toute tuile."""
        def disk(radius):
            return [
                (dx, dy)
                for dx in range(-radius, radius + 1)
                for dy in range(-radius, radius + 1)
            ]

        def manhattan(ax, ay, bx, by):
            return abs(ax - bx) + abs(ay - by)

        for radius in (0, 1, 4, 16):
            tiles = disk(radius)
            for distance in (1, 6):
                bound = 2 * radius + distance
                corner = (radius, radius)
                keep = (radius, radius + distance - 1)
                self.assertEqual(manhattan(0, 0, *keep), bound - 1)
                self.assertEqual(
                    min(manhattan(keep[0], keep[1], dx, dy) for dx, dy in tiles),
                    distance - 1,
                )
                drop = (radius, radius + distance)
                self.assertEqual(manhattan(0, 0, *drop), bound)
                self.assertEqual(
                    min(manhattan(drop[0], drop[1], dx, dy) for dx, dy in tiles),
                    distance,
                )
                self.assertEqual(
                    min(manhattan(corner[0], corner[1], dx, dy) for dx, dy in tiles),
                    0,
                )
                limit = bound + 2
                for sx in range(-limit, limit + 1):
                    for sy in range(-limit, limit + 1):
                        if manhattan(0, 0, sx, sy) < bound:
                            continue
                        nearest = min(manhattan(sx, sy, dx, dy) for dx, dy in tiles)
                        self.assertGreaterEqual(nearest, distance)


if __name__ == "__main__":
    unittest.main()
