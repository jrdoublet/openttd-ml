"""Contrats preparatoires V308 : sonde passive des blocs 8x8.

Les tests de geometrie se jouent entierement en Python. Les tests de contrat
doivent rester rouges jusqu'a l'integration de probe_v308.nut (file B, etape 3).
Aucun moteur OpenTTD ni banc n'est necessaire.
"""

import re
import tempfile
import unittest
from collections import deque
from pathlib import Path

from sweeps.diag_v308_carto import read_blocks, summarize


AI = Path(__file__).resolve().parents[1] / "ai" / "OpexAI"
SIDE = 8
V307 = ((4, 4), (2, 2), (6, 2), (2, 6), (6, 6))
RING = ((3, 1), (6, 2), (1, 5), (4, 6))
CENTERS = ((2, 3), (5, 4))
SIX = RING + CENTERS
ARM_NAMES = ("v307", "full6", "short6", "parity6", "flatdry6")


def read(name):
    file = AI / name
    return file.read_text(encoding="utf-8") if file.exists() else ""


def tile(*, sea=False, lake=False, river=False, house=False, town=False,
         height=0, high=None):
    """Classes excluantes pour l'eau ; autorite de ville independante des maisons."""
    if sum((sea, lake, river)) > 1:
        raise ValueError("types d'eau mutuellement exclusifs")
    return {"sea": sea, "lake": lake, "river": river, "house": house,
            "town": town, "min": height, "max": height if high is None else high}


def grid_with(*, changes=()):
    grid = {(x, y): tile() for y in range(SIDE) for x in range(SIDE)}
    grid.update(changes)
    return grid


def visible_counts(grid, points):
    seen = [grid[p] for p in points]
    return {
        "sea": sum(p["sea"] for p in seen),
        "lake": sum(p["lake"] for p in seen),
        "river": sum(p["river"] for p in seen),
        "house": sum(p["house"] for p in seen),
        "town": sum(p["town"] for p in seen),
        "height_delta": max(p["max"] for p in seen) - min(p["min"] for p in seen),
    }


def decisive(ring_values):
    """Court-circuit V308(c) : 2 eaux non fluviales, 2 maisons, 3 autorites, relief >=4."""
    counts = visible_counts({p: t for p, t in zip(RING, ring_values)}, RING)
    return (counts["sea"] + counts["lake"] >= 2
            or counts["house"] >= 2 or counts["town"] >= 3
            or counts["height_delta"] >= 4)


def flat_dry(ring_values):
    """V308(e) : les deux centres ne sont lus que si la peripherie est plate et seche."""
    counts = visible_counts({p: t for p, t in zip(RING, ring_values)}, RING)
    return (counts["height_delta"] == 0
            and counts["sea"] + counts["lake"] + counts["river"] == 0)


def motif_points(name, grid, bx=0, by=0):
    """Transcription Python des cinq variantes du prompt, sans appels Squirrel."""
    if name == "v307":
        return V307
    if name == "full6":
        return SIX
    if name == "parity6":
        # Convention proposable : deplacer les six points de (+1,+1) sur les
        # blocs impairs, sans deborder du bloc. A confirmer avant integration.
        delta = (bx + by) % 2
        return tuple((x + delta, y + delta) for x, y in SIX)
    ring_values = tuple(grid[p] for p in RING)
    if name == "short6":
        return RING if decisive(ring_values) else SIX
    if name == "flatdry6":
        return SIX if flat_dry(ring_values) else RING
    raise ValueError(name)


def river_crosses(grid):
    """Verite : composante de riviere connexe a 4 voisins, bords opposes du 8x8."""
    river = {pos for pos, t in grid.items() if t["river"]}
    visited = set()
    for start in river:
        if start in visited:
            continue
        component = {start}
        pending = deque([start])
        visited.add(start)
        while pending:
            x, y = pending.popleft()
            for neighbor in ((x + 1, y), (x - 1, y), (x, y + 1), (x, y - 1)):
                if neighbor in river and neighbor not in visited:
                    visited.add(neighbor)
                    component.add(neighbor)
                    pending.append(neighbor)
        xs = {x for x, _ in component}
        ys = {y for _, y in component}
        if ({0, SIDE - 1} <= xs) or ({0, SIDE - 1} <= ys):
            return True
    return False


def squirrel_offsets(source, name):
    """Contrat d'interface propose : tables globales explicites de points [x,y]."""
    match = re.search(rf"\b{name}\s*<-\s*(\[.*?\]);", source, re.S)
    if match is None:
        return None
    return tuple((int(x), int(y)) for x, y in re.findall(
        r"\[\s*(\d+)\s*,\s*(\d+)\s*\]", match.group(1)))


class TestV308Geometry(unittest.TestCase):
    def test_six_points_cover_each_interior_row_and_column(self):
        self.assertEqual(len(SIX), 6)
        self.assertEqual({x for x, _ in SIX}, set(range(1, 7)))
        self.assertEqual({y for _, y in SIX}, set(range(1, 7)))
        self.assertEqual(len(set(SIX)), 6)
        self.assertEqual(len({(x <= 3, y <= 3) for x, y in RING}), 4)

    def test_each_straight_interior_river_hits_exactly_one_six_point(self):
        for index in range(1, 7):
            horizontal = {(x, index) for x in range(SIDE)}
            vertical = {(index, y) for y in range(SIDE)}
            self.assertEqual(len(horizontal.intersection(SIX)), 1)
            self.assertEqual(len(vertical.intersection(SIX)), 1)
        # Angle mort connu des cinq points V307 : lignes 1,3,5.
        self.assertFalse({(x, 3) for x in range(SIDE)}.intersection(V307))
        self.assertTrue({(x, 3) for x in range(SIDE)}.intersection(SIX))

    def test_river_truth_requires_one_connected_component_across_opposite_edges(self):
        line = grid_with(changes={(x, 3): tile(river=True) for x in range(SIDE)})
        self.assertTrue(river_crosses(line))
        disconnected = grid_with(changes={
            **{(x, 3): tile(river=True) for x in (0, 1, 2)},
            **{(x, 5): tile(river=True) for x in (5, 6, 7)},
        })
        self.assertFalse(river_crosses(disconnected))
        diagonal = grid_with(changes={(i, i): tile(river=True) for i in range(SIDE)})
        self.assertFalse(river_crosses(diagonal))

    def test_decisive_short_circuit_is_precisely_three_classes(self):
        self.assertFalse(decisive((tile(),) * 4))
        self.assertTrue(decisive((tile(sea=True), tile(lake=True), tile(), tile())))
        self.assertFalse(decisive((tile(river=True), tile(river=True), tile(), tile())))
        self.assertTrue(decisive((tile(house=True), tile(house=True), tile(), tile())))
        self.assertTrue(decisive((tile(town=True),) * 3 + (tile(),)))
        self.assertFalse(decisive((tile(town=True),) * 2 + (tile(),) * 2))
        self.assertTrue(decisive((tile(height=0), tile(height=4), tile(), tile())))
        self.assertFalse(decisive((tile(height=0), tile(height=3), tile(), tile())))

    def test_short_and_flat_dry_read_centers_on_nondecisive_relief(self):
        grid = grid_with(changes={RING[0]: tile(height=0), RING[1]: tile(height=2),
                                  CENTERS[0]: tile(river=True)})
        self.assertEqual(motif_points("short6", grid), SIX)
        self.assertEqual(motif_points("flatdry6", grid), RING)
        self.assertIn(CENTERS[0], motif_points("short6", grid))
        self.assertNotIn(CENTERS[0], motif_points("flatdry6", grid))

    def test_decisive_mountain_can_hide_river_even_with_six_point_geometry(self):
        grid = grid_with(changes={RING[0]: tile(height=0), RING[1]: tile(height=5),
                                  CENTERS[1]: tile(river=True)})
        self.assertNotIn(CENTERS[1], motif_points("short6", grid))
        self.assertIn(CENTERS[1], motif_points("full6", grid))

    def test_flat_dry_centers_are_conditional(self):
        clear = grid_with()
        self.assertEqual(motif_points("flatdry6", clear), SIX)
        wet = grid_with(changes={RING[0]: tile(river=True)})
        self.assertEqual(motif_points("flatdry6", wet), RING)
        city = grid_with(changes={RING[0]: tile(house=True)})
        self.assertEqual(motif_points("flatdry6", city), SIX)

    def test_parity_shift_remains_inside_block_and_reaches_edge_band(self):
        grid = grid_with()
        self.assertEqual(motif_points("parity6", grid, bx=2, by=2), SIX)
        shifted = motif_points("parity6", grid, bx=1, by=2)
        self.assertEqual(shifted, tuple((x + 1, y + 1) for x, y in SIX))
        self.assertTrue(all(0 <= x < SIDE and 0 <= y < SIDE for x, y in shifted))
        self.assertTrue(any(x == 7 or y == 7 for x, y in shifted))

    def test_all_five_patterns_and_fixed_full_truth_cardinality(self):
        grid = grid_with()
        self.assertEqual(len(grid), 64)
        self.assertEqual([len(motif_points(name, grid)) for name in ARM_NAMES],
                         [5, 6, 6, 6, 6])
        self.assertEqual(sum(visible_counts(grid, SIX)[c]
                             for c in ("sea", "lake", "river", "house")), 0)


class TestV308SourceContracts(unittest.TestCase):
    def setUp(self):
        self.module = read("probe_v308.nut")

    def test_flag_defaults_to_zero_and_is_loaded_once(self):
        info = read("info.nut")
        block = re.search(r'name\s*=\s*"v308_carto_probe",(.*?)\}\);', info, re.S)
        self.assertIsNotNone(block, "Declaration AddSetting v308_carto_probe manquante")
        for level in ("easy", "medium", "hard", "custom"):
            self.assertRegex(block.group(1), rf"{level}_value\s*=\s*0\b")
        self.assertRegex(block.group(1), r"min_value\s*=\s*0\b")
        self.assertRegex(block.group(1), r"max_value\s*=\s*1\b")
        self.assertEqual(read("settings.nut").count('GetSetting("v308_carto_probe")'), 1)
        self.assertIn("V308_CARTO_PROBE <- 0;", read("globals_pre.nut"))
        self.assertIn("V308_DONE <- false;", read("globals_pre.nut"))

    def test_loaded_module_and_one_guarded_hook_per_loop(self):
        main = read("main.nut")
        profiled = read("probes.nut")
        hook = "if (V308_CARTO_PROBE > 0) OpexV308MaybeRun(this._loadedFromSave);"
        self.assertEqual(main.count('require("probe_v308.nut");'), 1)
        self.assertEqual(main.count(hook), 1)
        self.assertEqual(profiled.count(hook), 1)
        self.assertIn("function OpexV308MaybeRun(loadedFromSave)", self.module)
        self.assertIn("if (V308_DONE || loadedFromSave) return;", self.module)
        self.assertIn("OPEX_START_YEAR + V307_PROBE_YEAR", self.module)
        self.assertRegex(self.module, r"V308_DONE\s*=\s*true\s*;")

    def test_sample_count_bounds_and_truth_tile_apis(self):
        self.assertIn("400", self.module)
        self.assertIn("AIBase.RandRange(", self.module)
        self.assertIn("AIMap.GetMapSizeX()", self.module)
        self.assertIn("AIMap.GetMapSizeY()", self.module)
        for api in ("AITile.IsSeaTile", "AITile.IsRiverTile", "AITile.IsWaterTile",
                    "AITile.IsCoastTile", "AITile.IsHouseTile", "AITile.GetTownAuthority",
                    "AITile.GetMinHeight", "AITile.GetMaxHeight", "AITile.IsBuildable",
                    "AIRoad.IsRoadTile"):
            self.assertIn(api + "(", self.module)

    def test_peripheral_and_central_coordinates_are_auditable(self):
        self.assertEqual(squirrel_offsets(self.module, "V308_PERIPHERAL"), RING)
        self.assertEqual(squirrel_offsets(self.module, "V308_CENTRAL"), CENTERS)

    def test_five_arm_logs_and_opcode_measurement(self):
        self.assertIn('"V308_BLOCK"', self.module)
        for name in ARM_NAMES:
            self.assertIn(name, self.module)
        self.assertTrue("OpexOpsMeasureBegin(" in self.module
                        or "AIController.GetOpsTillSuspend()" in self.module)
        self.assertTrue("OpexOpsMeasureEnd(" in self.module
                        or self.module.count("AIController.GetOpsTillSuspend()") >= 2)

    def test_module_has_no_forbidden_squirrel_constructs(self):
        self.assertTrue(self.module, "module probe_v308.nut absent")
        self.assertNotIn("function(", self.module)
        self.assertNotIn(".find(", self.module)
        self.assertNotIn(".Valuate(", self.module)  # Ne pas elargir l'inventaire V262.
        for name in ("clone", "base", "parent", "pass"):
            self.assertNotRegex(self.module, rf"\blocal\s+{name}\b")


class TestV308Diagnostics(unittest.TestCase):
    def test_river_seen_does_not_imply_a_crossing_and_logs_remain_parseable(self):
        arms = []
        for name in ARM_NAMES:
            arms.extend((f"{name}_ops=320", f"{name}_relief=0",
                         f"{name}_river={1 if name == 'full6' else 0}"))
        line = " ".join(arms)
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "seed42.log"
            path.write_text(
                "[0] [I] OPEX 1970-1-1 V308_BLOCK i=0 bx=3 by=2 "
                "t_sea=0 t_river=8 t_river_cross=1 t_relief=0 " + line + "\n"
                "[0] [I] OPEX 1970-1-1 V308_BLOCK i=1 bx=4 by=2 "
                "t_sea=0 t_river=1 t_river_cross=0 t_relief=0 " + line + "\n",
                encoding="utf-8")
            blocks = list(read_blocks([path]))
        self.assertEqual(len(blocks), 2)
        rows = {row["motif"]: row for row in summarize(blocks)}
        self.assertEqual(rows["full6"]["classes"]["river_cross"]["missed"], 0)
        self.assertEqual(rows["full6"]["classes"]["river_cross"]["false_pos"], 1)
        self.assertEqual(rows["v307"]["classes"]["river_cross"]["missed"], 1)


if __name__ == "__main__":
    unittest.main()
