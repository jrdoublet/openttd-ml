#!/usr/bin/env python3
"""Contrats air_site_funnel : defaut 0 inchange, entonnoir opt-in."""

from __future__ import annotations

import hashlib
import re
import unittest
from pathlib import Path

from n75_mc_legacy import historical_bytes
from test_v94_air_site_list import list_anchors

ROOT = Path(__file__).resolve().parents[1]
AI = ROOT / "ai" / "OpexAI"
AIR_SITES_SHA = "1ef05fc3b922e34d5ed800a52d9b5816e2d958492e434075bd0fe1e4e5a546f7"


def source(name):
    return (AI / name).read_text(encoding="utf-8")


def body(text, signature):
    start = text.index(signature)
    brace = text.index("{", start)
    depth = 0
    for idx in range(brace, len(text)):
        if text[idx] == "{":
            depth += 1
        elif text[idx] == "}":
            depth -= 1
            if depth == 0:
                return text[start:idx + 1]
    raise AssertionError(signature)


def funnel_box(tx, ty, map_x, map_y, width, height, radius=25):
    off_x = width - 1
    off_y = height - 1
    min_x = max(0, tx - radius)
    min_y = max(0, ty - radius)
    max_x = min(tx + radius, map_x - off_x - 1, map_x - 1)
    max_y = min(ty + radius, map_y - off_y - 1, map_y - 1)
    if min_x > max_x or min_y > max_y:
        return None
    return min_x, min_y, max_x, max_y


def inset_void(box, map_x, map_y, north=1, east_void=True, south_void=True):
    """Meme arithmetique que OpexAirFunnelInsetVoid, bords joues en parametres."""
    if box is None:
        return None
    min_x, min_y, max_x, max_y = box
    if min_x < north:
        min_x = north
    if min_y < north:
        min_y = north
    limit_x = map_x - 2 if east_void else map_x - 1
    limit_y = map_y - 2 if south_void else map_y - 1
    if max_x > limit_x:
        max_x = limit_x
    if max_y > limit_y:
        max_y = limit_y
    if min_x > max_x or min_y > max_y:
        return None
    return min_x, min_y, max_x, max_y


def funnel_domain(tx, ty, map_x, map_y, width, height, radius=25, box=None):
    """Meme ensemble que OpexAirFunnelBox + DropCore + ClipDistance."""
    if box is None:
        box = funnel_box(tx, ty, map_x, map_y, width, height, radius)
    if box is None:
        return set()
    min_x, min_y, max_x, max_y = box
    span = height - 1
    width_gap = width - 1
    kept = set()
    for y in range(min_y, max_y + 1):
        bottom = y + span
        if ty < y:
            dy = y - ty
        elif ty > bottom:
            dy = ty - bottom
        else:
            dy = 0
        if dy > radius:
            continue
        budget = radius - dy
        ax_lo = max(min_x, tx - width_gap - budget)
        ax_hi = min(max_x, tx + budget)
        if ax_lo > ax_hi:
            continue
        for x in range(ax_lo, ax_hi + 1):
            if max(abs(x - tx), abs(y - ty)) < 4:
                continue
            kept.add(y * map_x + x)
    return kept


class AirSiteFunnelContracts(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.info = source("info.nut")
        cls.settings = source("settings.nut")
        cls.globals = source("globals_pre.nut")
        cls.sites = source("air_sites.nut")
        cls.funnel = source("air_site_funnel.nut")
        cls.builder = source("builder_air.nut")
        cls.regen = source("po01c_regen.nut")

    def test_mode0_historical_bytes_and_spiral_body(cls):
        legacy = historical_bytes("air_sites.nut", (AI / "air_sites.nut").read_bytes())
        cls.assertEqual(hashlib.sha256(legacy).hexdigest(), AIR_SITES_SHA)
        first = body(cls.sites, "function OpexAirFindSite(")
        cls.assertIn("return OpexAirFindSiteCatchmentListed(", first)
        cls.assertNotIn("AIR_SITE_FUNNEL", first)
        cls.assertNotIn("OpexAirFindSiteFunnel", first)
        log = body(cls.sites, "function OpexAirC96LogChoice(")
        cls.assertIn('" probes=" + used + " ops=" + ops', log)
        cls.assertIn("OpexOpsMeasureEnd(AIR_SITE_OPS_MARK)", log)

    def test_setting_default_zero_one_read(self):
        blocks = re.findall(
            r'AddSetting\(\{\s*name = "air_site_funnel".*?\}\);', self.info, re.S)
        self.assertEqual(len(blocks), 1)
        for level in ("easy", "medium", "hard", "custom"):
            self.assertIn(f"{level}_value = 0", blocks[0])
        self.assertIn("min_value = 0, max_value = 1", blocks[0])
        self.assertEqual(self.settings.count('GetSetting("air_site_funnel")'), 1)
        self.assertIn("AIR_SITE_FUNNEL = (airSiteFunnel == 1) ? 1 : 0;", self.settings)
        self.assertIn("if (AIR_SITE_FUNNEL > 0) OpexAirFunnelInstall();", self.settings)
        self.assertIn("AIR_SITE_FUNNEL <- 0;", self.globals)
        self.assertIn("AIR_SITE_FUNNEL_BATCH <- 5;", self.globals)
        self.assertIn("AIR_SITE_OPS_MARK <- null;", self.globals)
        self.assertLess(
            self.builder.index('require("air_sites.nut");'),
            self.builder.index('require("air_site_funnel.nut");'),
        )

    def test_wrapper_measures_both_modes_and_keeps_spiral(self):
        wrap = body(self.funnel, "function OpexAirFindSite(")
        self.assertLess(wrap.index("OpexOpsMeasureBegin()"), wrap.index("AIR_SITE_FUNNEL > 0"))
        self.assertLess(wrap.index("OpexAirFindSiteFunnel("), wrap.index("OpexAirFindSiteSpiral("))
        self.assertIn("OpexAirFindSiteSpiral <- OpexAirFindSite;", self.funnel)
        install = body(self.funnel, "function OpexAirFunnelInstall(")
        self.assertIn("if (AIR_SITE_FUNNEL <= 0) return;", install)
        self.assertIn("::OpexPO01CAirFindSite <- OpexPO01CAirFindSiteFunnel;", install)

    def test_native_filter_order_and_no_buildable_list_filter(self):
        tiles = body(self.funnel, "function OpexAirFunnelTiles(")
        order = [
            "OpexAirFunnelInsetVoid(",
            "tiles.AddRectangle(",
            "OpexAirFunnelDropCore(",
            "OpexAirFunnelClipDistance(",
            "tiles.Valuate(AITile.IsBuildableRectangle, w, h)",
            "tiles.KeepValue(1)",
            "tiles.Valuate(AITile.IsWaterTile)",
            "tiles.Valuate(AITile.IsCoastTile)",
            "tiles.Valuate(AITile.GetClosestTown)",
            "tiles.Valuate(AIAirport.GetNearestTown, airport.type)",
            "tiles.Valuate(AITile.GetCargoAcceptance, paxCargo, w, h, radius)",
            "tiles.KeepAboveValue(7)",
            "tiles.Valuate(AITile.GetCargoProduction, paxCargo, w, h, radius)",
            "tiles.KeepAboveValue(0)",
            "tiles.Sort(AIList.SORT_BY_VALUE, AIList.SORT_DESCENDING)",
        ]
        at = -1
        for token in order:
            found = tiles.index(token)
            self.assertGreater(found, at, token)
            at = found
        # KeepValue(1) precede le nivellement : CheapOk refuse deja ces ancres.
        self.assertEqual(self.funnel.count("tiles.Valuate(AITile.IsBuildableRectangle, w, h)"), 1)
        self.assertLess(
            tiles.index("tiles.KeepValue(1)"),
            tiles.index("tiles.Valuate(AITile.IsWaterTile)"),
        )
        self.assertNotIn("valid >= C96_AIR_SITE_MAX_VALID", self.funnel)
        self.assertNotIn("score > bestScore", self.funnel)

    def test_stops_at_first_valid_and_reuses_cache_rules(self):
        search = body(self.funnel, "function OpexAirFunnelSearch(")
        choice = search.index(
            "OpexAirC96LogChoice(town, airport, anchor, score, site, score, 1, ring, ring, used)")
        self.assertLess(choice, search.index("return site;"))
        self.assertLess(search.index("OpexAirFootprintCheapOk(anchor, airport)"),
                        search.index("OpexAirFunnelProbe("))
        self.assertLess(search.index("probed.limited"), search.index("used++;"))
        self.assertIn("AIR_SITE_CACHE[key] <- anchor;", search)
        self.assertIn("while (batch < AIR_SITE_FUNNEL_BATCH && !tiles.IsEnd())", search)
        self.assertIn('OpexAirFunnelTrace(town, airport, raw, afterNative, checked, used, 1, score, 1, "ok")',
                      search)
        probe = body(self.funnel, "function OpexAirFunnelProbe(")
        self.assertIn("execLevels < 3", probe)
        self.assertIn("AIStation.STATION_NEW", probe)
        self.assertLess(probe.index("local probe = AITestMode();"), probe.index("AIError.GetLastError()"))
        reuse = body(self.funnel, "function OpexAirFunnelReuse(")
        self.assertNotIn("execLevels", reuse)
        self.assertIn("OpexAirCanLevelFootprint(cachedAnchor, airport, town.id)", reuse)
        self.assertIn("AIR_SITE_CACHE[key] <- null;", reuse)
        self.assertIn('return { kind = "negative", site = null };', reuse)
        self.assertIn('return { kind = "site", site = { town = town, anchor = cachedAnchor } };', reuse)
        budget = body(self.funnel, "function OpexAirFunnelBudget(")
        self.assertIn('OpexAirC78NoteNoSite(probes, "no_site_budget")', budget)
        self.assertIn("if (useSiteCache && used >= allowance) AIR_SITE_CACHE[key] <- null;", budget)

    def test_distance_rows_match_the_spiral_domain(self):
        clip = body(self.funnel, "function OpexAirFunnelClipDistance(")
        for token in (
            "if (townY < y) dy = y - townY;",
            "else if (townY > bottom) dy = townY - bottom;",
            "if (dy > radius)",
            "local budget = radius - dy;",
            "local axLo = townX - widthGap - budget;",
            "local axHi = townX + budget;",
        ):
            self.assertIn(token, clip)
        # y=100 garde l'intersection avec la boite, pas l'ancre 72 hors Chebyshev.
        self.assertEqual(
            _row_span(100, 100, 100, 4, 3, 25, 75, 125), (75, 125))
        self.assertEqual(_row_span(100, 100, 120, 4, 3, 25, 75, 125), (92, 105))
        self.assertEqual(_row_span(100, 100, 80, 4, 3, 25, 75, 125), (90, 107))
        self.assertIsNone(_row_span(100, 100, 130, 4, 3, 25, 75, 125))
        sizes = ((1, 1), (4, 3), (6, 6), (2, 5))
        for map_size in (64, 256):
            positions = (
                (map_size // 2, map_size // 2),
                (0, 0),
                (3, 10),
                (map_size - 1, map_size - 1),
                (map_size - 8, 4),
                (6, map_size - 2),
            )
            for tx, ty in positions:
                for width, height in sizes:
                    with self.subTest(map_size=map_size, tx=tx, ty=ty, width=width, height=height):
                        spiral = set(list_anchors(tx, ty, map_size, map_size, width, height))
                        self.assertEqual(
                            funnel_domain(tx, ty, map_size, map_size, width, height),
                            spiral,
                        )

    def test_void_border_inset_keeps_playable_anchors(self):
        inset = body(self.funnel, "function OpexAirFunnelInsetVoid(")
        self.assertLess(
            inset.index("!AIMap.IsValidTile(AIMap.GetTileIndex(0, 1))"),
            inset.index("if (minX < north) minX = north;"),
        )
        self.assertIn("if (minY < north) minY = north;", inset)
        self.assertIn("limitX = mapX - 2;", inset)
        self.assertIn("limitY = mapY - 2;", inset)
        tiles = body(self.funnel, "function OpexAirFunnelTiles(")
        self.assertLess(tiles.index("OpexAirFunnelInsetVoid("), tiles.index("tiles.AddRectangle("))
        # Villes du smoke 1 : boite collee a x=0 ou y=0, domaine jouable non vide.
        smoke_towns = ((19, 89), (12, 170), (21, 49), (167, 24))
        for tx, ty in smoke_towns:
            raw = funnel_box(tx, ty, 256, 256, 6, 6)
            self.assertTrue(raw[0] == 0 or raw[1] == 0, raw)
            played = inset_void(raw, 256, 256)
            self.assertIsNotNone(played)
            self.assertGreaterEqual(played[0], 1)
            self.assertGreaterEqual(played[1], 1)
            self.assertLessEqual(played[2], 254)
            self.assertLessEqual(played[3], 254)
            domain = funnel_domain(tx, ty, 256, 256, 6, 6, box=played)
            spiral = set(list_anchors(tx, ty, 256, 256, 6, 6))
            playable = {
                tile for tile in spiral
                if 1 <= (tile % 256) <= 254 and 1 <= (tile // 256) <= 254
            }
            self.assertEqual(domain, playable)
            self.assertGreater(len(domain), 1000)

    def test_po01c_adapter_is_opt_in_and_syntax_stays_plain(self):
        adapter = body(self.regen, "function OpexPO01CAirFindSiteFunnel(")
        self.assertIn(
            "po01dResult.value = OpexAirFindSite(town, airport, probes, requiredSlotTownId);",
            adapter,
        )
        self.assertIn("yield null;", adapter)
        self.assertNotIn("yield", self.funnel)
        self.assertNotIn("function(", self.funnel)
        self.assertNotIn(".find(", self.funnel)
        self.assertNotRegex(
            self.funnel, r"\blocal\s+(clone|base|parent|static|delegate|vargc|vargv|resume|yield)\b")
        trace = body(self.funnel, "function OpexAirFunnelTrace(")
        for field in (
            '"AIR_SITE_FUNNEL town="',
            '" type="',
            '" tiles="',
            '" after_native="',
            '" checked="',
            '" probes="',
            '" ok="',
            '" score="',
            '" best_possible="',
            '" ops="',
            '" reason="',
        ):
            self.assertIn(field, trace)


def _row_span(town_x, town_y, y, width, height, radius, min_x, max_x):
    bottom = y + height - 1
    if town_y < y:
        dy = y - town_y
    elif town_y > bottom:
        dy = town_y - bottom
    else:
        dy = 0
    if dy > radius:
        return None
    budget = radius - dy
    ax_lo = max(min_x, town_x - (width - 1) - budget)
    ax_hi = min(max_x, town_x + budget)
    if ax_lo > ax_hi:
        return None
    return ax_lo, ax_hi


if __name__ == "__main__":
    unittest.main()
