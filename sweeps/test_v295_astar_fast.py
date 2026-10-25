"""Contrats V295 : deux optimisations d'opcodes exactes de l'A* rail V129.

Verifie :
- retrait du reglage v295_astar_fast et conservation de la constante active 1 ;
- scan de collision toujours present en cas de collision Bloom ;
- filtre de Bloom actif avec modulo 61 ;
- champ _bloom sur Path et initialisation des sources ;
- garde ("_bloom" in node) a l'insertion des sources ;
- dedoublonnage des buts pour l'estimation toujours actif ;
- absence de closure et absence de .find() ;
- equivalence mathematique exacte du filtre de Bloom et du dedoublonnage.
"""
import re
import unittest
from pathlib import Path

from test_b5_rail_persistence import function_body

AI = Path(__file__).resolve().parents[1] / "ai" / "OpexAI"


def read(name):
    return (AI / name).read_text(encoding="utf-8")


class TestV295AstarFast(unittest.TestCase):
    def setUp(self):
        self.info = read("info.nut")
        self.settings = read("settings.nut")
        self.globals_pre = read("globals_pre.nut")
        self.v129 = read("pathfinder_v90/v129.nut")

    def test_adopted_fast_path_is_constant_and_not_a_setting(self):
        self.assertNotIn('name = "v295_astar_fast"', self.info)
        self.assertNotIn('GetSetting("v295_astar_fast")', self.settings)
        self.assertIn("const V295_ASTAR_FAST = 1;", self.globals_pre)

    def test_findpath_collision_scan_and_active_bloom_filter(self):
        body = function_body(self.v129, "function OpexAyStarV129::FindPath(iterations)")
        self.assertIsNotNone(body, "OpexAyStarV129::FindPath doit exister")

        # Le chemin ON est inconditionnel et ne depend plus du reglage.
        self.assertNotIn("fastAstar", body)

        # Le scan de collision historique est toujours present
        self.assertIn("local scan_path = path._prev;", body)
        self.assertIn("while (scan_path != null) {", body)
        self.assertIn("scan_path._tile == cur_tile", body)
        self.assertIn("scan_path = scan_path._prev;", body)

        # Le filtre de Bloom utilise % 61, puis scanne si collision possible.
        self.assertIn("cur_tile % 61", body)
        self.assertIn("path._prev._bloom", body)
        self.assertRegex(body, r'path\._prev\._bloom\s*&\s*\(\s*1\s*<<\s*\(\s*cur_tile\s*%\s*61\s*\)\s*\)\s*\)\s*==\s*0')

    def test_path_bloom_field_and_propagation(self):
        # Champ _bloom sur la classe Path
        path_block = re.search(r'class OpexAyStarV129\.Path\s*\{(.*?)\};', self.v129, re.S)
        self.assertIsNotNone(path_block, "Classe OpexAyStarV129.Path introuvable")
        self.assertIn("_bloom = 0;", path_block.group(1))

        # Propagation dans FindPath avec % 61
        body = function_body(self.v129, "function OpexAyStarV129::FindPath(iterations)")
        self.assertIn("path._bloom | (1 << (ntile % 61))", body)

        # Chaque voisin propage le bloom (l'ancien chemin sans bloom est mort).
        self.assertIn("this.Path(path, ntile, ndir, c, path._bloom | (1 << (ntile % 61)))", body)
        self.assertNotIn("this.Path(path, ntile, ndir, c)", body)

    def test_sources_bloom_initialization_and_type_protection(self):
        # OpexAyStarV129::InitializePath initialise le bloom pour les sources array
        body_ay = function_body(self.v129, "function OpexAyStarV129::InitializePath(sources, goals, ignored_tiles = [])")
        self.assertIn("node[0] % 61", body_ay)
        # Protection ("_bloom" in node) a l'insertion des sources
        self.assertIn('"_bloom" in node', body_ay)

        # OpexRailPathFinderV129::InitializePath initialise p0 et nsources avec bloom
        rpf_block = re.search(r'class OpexRailPathFinderV129.*?\{(.*?)\nclass', self.v129, re.S).group(1)
        self.assertIn("node[1] % 61", rpf_block)
        self.assertIn("node[0] % 61", rpf_block)

    def test_goal_coords_deduplication_always_active(self):
        rpf_block = re.search(r'class OpexRailPathFinderV129.*?\{(.*?)\nclass', self.v129, re.S).group(1)
        self.assertNotIn("if (V295_ASTAR_FAST)", rpf_block)
        self.assertIn("seen", rpf_block)
        self.assertIn("seen[tile] <- true;", rpf_block)
        # Ne modifie pas rail.nut (V90)
        rail_nut = read("pathfinder_v90/rail.nut")
        self.assertNotIn("V295_ASTAR_FAST", rail_nut)

    def test_no_closure_and_no_find(self):
        # Pas de closure Squirrel capturant des locaux
        self.assertNotRegex(self.v129, r"function\s*\(")
        # Pas d'utilisation de .find() qui n'existe pas sur les tableaux Squirrel
        self.assertNotIn(".find(", self.v129)

    def test_bloom_exactness_no_false_negatives(self):
        # Simulation d'un chemin avec filtre de Bloom 61 bits
        # Verifie qu'aucun ancetre reel n'est jamais ignore (zero faux negatif)
        import random
        rng = random.Random(42)
        tiles = [rng.randint(0, 4194303) for _ in range(100)]

        bloom = 0
        visited = set()
        for t in tiles:
            # Avant insertion, si t est dans visited, (bloom & (1 << (t % 61))) doit etre != 0
            if t in visited:
                self.assertNotEqual(bloom & (1 << (t % 61)), 0,
                                    "Filtre de Bloom: faux negatif impossible!")
            visited.add(t)
            bloom |= (1 << (t % 61))

        # Pour toute tuile de la chaine, le filtre de Bloom doit avoir le bit a 1
        for t in visited:
            self.assertNotEqual(bloom & (1 << (t % 61)), 0)

    def test_goal_coords_deduplication_preserves_minimum_distance(self):
        # Simulation de buts avec tuiles dupliquees (paires [tile, station_exit])
        # Verifie que le minimum sur _goalCoords est strictement identique avec ou sans doublons
        goals = [
            [1050, 1049],
            [1050, 1051],
            [2040, 2039],
            [2040, 2041],
        ]
        # Sans dedoublonnage
        coords_all = [{"tile": g[0], "x": g[0] % 256, "y": g[0] // 256} for g in goals]
        # Avec dedoublonnage
        seen = {}
        coords_dedup = []
        for g in goals:
            if g[0] in seen:
                continue
            seen[g[0]] = True
            coords_dedup.append({"tile": g[0], "x": g[0] % 256, "y": g[0] // 256})

        self.assertEqual(len(coords_dedup), 2)
        self.assertEqual(len(coords_all), 4)

        # Calcul d'estimation sur diverses tuiles de test
        diag_cost2 = 140
        straight_cost = 100
        for test_tile in [500, 1048, 1500, 2050, 3000]:
            cx, cy = test_tile % 256, test_tile // 256

            min_all = 10000000
            for g in coords_all:
                dx = abs(cx - g["x"])
                dy = abs(cy - g["y"])
                min_d = min(dx, dy)
                max_d = max(dx, dy)
                cost = min_d * diag_cost2 + (max_d - min_d) * straight_cost
                if cost < min_all:
                    min_all = cost

            min_dedup = 10000000
            for g in coords_dedup:
                dx = abs(cx - g["x"])
                dy = abs(cy - g["y"])
                min_d = min(dx, dy)
                max_d = max(dx, dy)
                cost = min_d * diag_cost2 + (max_d - min_d) * straight_cost
                if cost < min_dedup:
                    min_dedup = cost

            self.assertEqual(min_all, min_dedup,
                             f"Estimation doit etre identique pour tile {test_tile}")


if __name__ == "__main__":
    unittest.main()
