#!/usr/bin/env python3
"""Contrats statiques V94 : réglages et ordre des anneaux paresseux.

Le modèle rejoue, pour chaque r, le carré clampé moins le carré intérieur,
puis l'ordre (X, index de tuile). Sur une carte puissance de 2 l'index
croissant à X égal est Y croissant, donc (dx, dy). Aucun appel OpenTTD.
"""

from __future__ import annotations

import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

import sys

sys.path.insert(0, str(ROOT / "sweeps"))
from campaign_freeze import parse_ai_settings, parse_ai_setting_specs


def _read(rel_path: str) -> str:
    return (ROOT / rel_path).read_text(encoding="utf-8")


def distance_to_rect(tx: int, ty: int, ax: int, ay: int, width: int, height: int) -> int:
    right = ax + width - 1
    bottom = ay + height - 1
    dx = (ax - tx) if tx < ax else ((tx - right) if tx > right else 0)
    dy = (ay - ty) if ty < ay else ((ty - bottom) if ty > bottom else 0)
    return dx + dy


def legacy_anchors(tx, ty, map_x, map_y, width, height, radius=25, apply_distance=True):
    """Suite d'ancres du triple boucle, après validité, bornes d'emprise et distance."""
    off_x = width - 1
    off_y = height - 1
    town = ty * map_x + tx
    found = []
    for radius_step in range(4, radius + 1):
        for dx in range(-radius_step, radius_step + 1):
            for dy in range(-radius_step, radius_step + 1):
                if abs(dx) != radius_step and abs(dy) != radius_step:
                    continue
                anchor = town + dx + dy * map_x
                if anchor < 0 or anchor >= map_x * map_y:
                    continue
                ax = anchor % map_x
                ay = anchor // map_x
                if ax + off_x >= map_x or ay + off_y >= map_y:
                    continue
                if apply_distance and distance_to_rect(tx, ty, ax, ay, width, height) > 25:
                    continue
                wrapped = (ax - tx) != dx or (ay - ty) != dy
                found.append((anchor, wrapped))
    return found


def ring_tiles(tx, ty, map_x, map_y, width, height, radius_step):
    """Anneau r : carré clampé moins l'intérieur, ordre (X, index de tuile)."""
    off_x = width - 1
    off_y = height - 1
    min_x = max(0, tx - radius_step)
    min_y = max(0, ty - radius_step)
    max_x = min(tx + radius_step, map_x - off_x - 1, map_x - 1)
    max_y = min(ty + radius_step, map_y - off_y - 1, map_y - 1)
    if min_x > max_x or min_y > max_y:
        return []
    inner = radius_step - 1
    in_min_x = max(min_x, tx - inner)
    in_min_y = max(min_y, ty - inner)
    in_max_x = min(max_x, tx + inner)
    in_max_y = min(max_y, ty + inner)
    tiles = []
    for ax in range(min_x, max_x + 1):
        for ay in range(min_y, max_y + 1):
            if in_min_x <= in_max_x and in_min_y <= in_max_y:
                if in_min_x <= ax <= in_max_x and in_min_y <= ay <= in_max_y:
                    continue
            tiles.append(ay * map_x + ax)
    tiles.sort(key=lambda tile: (tile % map_x, tile))
    return tiles


def list_anchors(tx, ty, map_x, map_y, width, height, radius=25, apply_distance=True):
    """Anneaux r = 4..radius concaténés. La distance filtre sans changer l'ordre."""
    found = []
    for radius_step in range(4, radius + 1):
        for anchor in ring_tiles(tx, ty, map_x, map_y, width, height, radius_step):
            ax = anchor % map_x
            ay = anchor // map_x
            if apply_distance and distance_to_rect(tx, ty, ax, ay, width, height) > 25:
                continue
            found.append(anchor)
    return found


class TestV94AirSiteListContract(unittest.TestCase):
    def test_settings_declared_and_loaded(self):
        info = _read("ai/OpexAI/info.nut")
        settings = _read("ai/OpexAI/settings.nut")
        globals_pre = _read("ai/OpexAI/globals_pre.nut")
        for setting_name in ("v94_air_site_list", "v94_air_site_check"):
            self.assertIn(f'name = "{setting_name}"', info)
            start = info.index(f'name = "{setting_name}"')
            block = info[start:info.index("});", start)]
            self.assertIn("flags = AICONFIG_BOOLEAN", block)
            expected = 1 if setting_name == "v94_air_site_list" else 0
            for field in ("custom_value", "easy_value", "medium_value", "hard_value"):
                self.assertIn(f"{field} = {expected}", block)
        self.assertIn(
            'V94_AIR_SITE_LIST = AIController.GetSetting("v94_air_site_list") != 0;',
            settings,
        )
        self.assertIn(
            'V94_AIR_SITE_CHECK = AIController.GetSetting("v94_air_site_check") != 0;',
            settings,
        )
        self.assertIn("V94_AIR_SITE_LIST <- true;", globals_pre)
        self.assertIn("V94_AIR_SITE_CHECK <- false;", globals_pre)

        defaults = parse_ai_settings(ROOT / "ai" / "OpexAI" / "info.nut")
        specs = parse_ai_setting_specs(ROOT / "ai" / "OpexAI" / "info.nut")
        self.assertEqual(defaults["v94_air_site_list"], 1)
        self.assertEqual(defaults["v94_air_site_check"], 0)
        for setting_name in ("v94_air_site_list", "v94_air_site_check"):
            self.assertTrue(specs[setting_name]["boolean"])

    def test_native_filters_and_legacy_loop_both_present(self):
        source = _read("ai/OpexAI/builder_air.nut")
        self.assertNotIn("OpexAirSiteAnchorBefore", source)
        self.assertNotIn("OpexAirFindSiteListAnchors", source)
        ring = source.split("function OpexAirFindSiteRing", 1)[1].split(
            "function OpexAirFindSiteListed", 1
        )[0]
        self.assertIn("tiles.Valuate(AITile.IsWaterTile);", ring)
        self.assertIn("tiles.KeepValue(0);", ring)
        self.assertIn("tiles.Valuate(AITile.IsCoastTile);", ring)
        self.assertIn("tiles.Valuate(AITile.GetClosestTown);", ring)
        self.assertIn("tiles.KeepValue(requiredSlotTownId);", ring)
        self.assertIn("tiles.Valuate(AIAirport.GetNearestTown, airport.type);", ring)
        self.assertIn("tiles.KeepValue(town.id);", ring)
        self.assertIn("tiles.Valuate(AIMap.GetTileX);", ring)
        self.assertIn("tiles.Sort(AIList.SORT_BY_VALUE, AIList.SORT_ASCENDING);", ring)
        self.assertIn("RemoveRectangle", ring)
        self.assertNotIn(".append(", ring)
        self.assertNotIn(".sort(", ring)

        listed = source.split("function OpexAirFindSiteListed", 1)[1].split(
            "function OpexAirV94Report", 1
        )[0]
        self.assertIn("for (local r = 4; r <= AIR_SITE_RADIUS; r++)", listed)
        self.assertIn("OpexAirFindSiteRing(", listed)
        self.assertIn("OpexAirDistanceToRect(town.tile, anchor, w, h) > 25", listed)
        self.assertIn("AITile.IsWaterTile(c4) || AITile.IsCoastTile(c4)", listed)
        self.assertIn("OpexAirFootprintCheapOk(anchor, airport)", listed)
        self.assertNotIn(".append(", listed)

        find_site = source.split("function OpexAirFindSite(town, airport, probes", 1)[1]
        self.assertIn("for (local r = 4; r <= AIR_SITE_RADIUS; r++)", find_site)
        self.assertIn("if (V94_AIR_SITE_LIST && !V94_AIR_SITE_CHECK)", find_site)
        self.assertIn('AILog.Info("V94_CHECK "', source)
        finish = source.split("function OpexAirV94Finish", 1)[1][:900]
        self.assertIn("OpexAirFindSiteListed(town, airport, copy, requiredSlotTownId, key, false);", finish)

    def test_x_then_tile_index_matches_dx_dy_inside_each_ring(self):
        """À X égal, l'index croissant est Y croissant, donc l'ordre (dx, dy)."""
        map_size = 64
        tx = ty = 30
        width, height = 4, 3
        for radius_step in (4, 5, 11, 25):
            historical = []
            for dx in range(-radius_step, radius_step + 1):
                for dy in range(-radius_step, radius_step + 1):
                    if abs(dx) != radius_step and abs(dy) != radius_step:
                        continue
                    ax = tx + dx
                    ay = ty + dy
                    if ax < 0 or ay < 0 or ax >= map_size or ay >= map_size:
                        continue
                    if ax + width - 1 >= map_size or ay + height - 1 >= map_size:
                        continue
                    historical.append(ay * map_size + ax)
            native = ring_tiles(tx, ty, map_size, map_size, width, height, radius_step)
            self.assertEqual(native, historical)
            self.assertEqual(native, sorted(native, key=lambda tile: (tile % map_size, tile)))
            shared_x = {}
            for tile in native:
                shared_x.setdefault(tile % map_size, []).append(tile)
            columns = [group for group in shared_x.values() if len(group) > 1]
            self.assertGreater(len(columns), 0)
            for group in columns:
                self.assertEqual(group, sorted(group))

    def test_rectangle_matches_ring_order_after_distance(self):
        sizes = (1, 1), (4, 3), (6, 6), (9, 11), (2, 2), (12, 8)
        for map_size in (64, 256):
            positions = (
                (map_size // 2, map_size // 2),
                (0, 0),
                (1, 2),
                (map_size - 1, map_size - 1),
                (map_size - 1, 3),
                (5, map_size - 1),
                (map_size - 10, map_size // 3),
                (30, 0),
            )
            for tx, ty in positions:
                for width, height in sizes:
                    legacy = legacy_anchors(tx, ty, map_size, map_size, width, height)
                    wrapped = [anchor for anchor, is_wrapped in legacy if is_wrapped]
                    self.assertEqual(
                        wrapped,
                        [],
                        f"débordement survivant map={map_size} town=({tx},{ty}) {width}x{height}",
                    )
                    expected = [anchor for anchor, _ in legacy]
                    got = list_anchors(tx, ty, map_size, map_size, width, height)
                    self.assertEqual(
                        got,
                        expected,
                        f"ordre map={map_size} town=({tx},{ty}) {width}x{height}",
                    )

    def test_wide_footprint_can_keep_a_wrapped_anchor(self):
        """Borne documentée : une emprise plus large que mapX - 49 peut garder un débordement."""
        legacy = legacy_anchors(63, 32, 64, 64, 20, 1)
        wrapped = [anchor for anchor, is_wrapped in legacy if is_wrapped]
        self.assertGreater(len(wrapped), 0)
        geometric = list_anchors(63, 32, 64, 64, 20, 1)
        self.assertNotIn(wrapped[0], geometric)


if __name__ == "__main__":
    unittest.main()
